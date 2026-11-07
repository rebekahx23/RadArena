"""Fresh, uncached arena demo. Never reads a saved candidate or resumes an old stage."""

import argparse
import hashlib
import random
import time
from pathlib import Path

import dspy

from .agents import InspectImage, PlanChecks
from .clinical_context import Indications
from .data import Sentence, Study
from .knowledge import load_pack
from .live import JUDGES, JUDGE_BACKUPS, MODEL, now, read, save
from .memory_policy import ReviewMemory, quarantine, rule_issues, valid_review
from .open_online import (Change, Lesson, OpenAssess, OpenAttack, OpenReview, ReviewOpen,
                          UpdateLessons, assess_with_correction, flatten, private_feedback,
                          promote, sha, validate_attack)
from .runtime import make_judge_model
from .tracing import AuditSession, audit_context


class LiveAttack(OpenAttack):
    correction: dict = dspy.InputField(desc="Empty initially. If a prior attempt was unchanged or malformed, try a different clinically plausible image-grounded change. Never force an unsupported attack.")


class Stopped(Exception):
    pass


class DemoRunner:
    def __init__(self, root, manifest):
        self.root, self.manifest = Path(root), Path(manifest)
        self.state = read(self.root / "live.json")
        self.config = self.state["options"]
        self.records = []

    def state_update(self, **fields):
        self.state.update(fields, updated_at=now())
        save(self.root / "live.json", self.state)

    def check_stop(self):
        if (self.root / "stop.requested").exists():
            raise Stopped()

    def cost(self):
        return sum(read(p, {}).get("accounted_cost_usd", 0) for p in self.root.glob("audit/*/budget.json"))

    def stage(self, name, role, phase, fn, model=MODEL, optional=False, fallback_model=None):
        directory = self.root / "audit" / name
        requested_model = model
        models = [model, model] + ([fallback_model, fallback_model] if fallback_model else [])
        for attempt, model in enumerate(models):
            self.check_stop()
            self.state_update(status="running", phase=phase, stage=name, role=role, retry=attempt, active_model=model,
                fallback_from=requested_model if model != requested_model else None)
            remaining = self.config["budget"] - self.cost()
            if remaining <= 0:
                raise RuntimeError("Spending cap reached before the next request")
            own = read(directory / "budget.json", {}).get("accounted_cost_usd", 0)
            audit = AuditSession(directory, min(1, remaining + own), 20)
            try:
                with audit_context(audit):
                    audit.set_context(stage=name, role=role, run=self.root.name, live=True, stage_attempt=attempt+1,
                        requested_model=requested_model, fallback_from=requested_model if model != requested_model else None)
                    lm = make_judge_model(model, cache=False)
                    with dspy.context(lm=lm, adapter=dspy.JSONAdapter(), track_usage=True):
                        result = fn(lm)
                if fallback_model:
                    result.update(requested_model=requested_model, model=model, fallback_used=model != requested_model,
                        fallback_reason="Primary reviewer unavailable after retry" if model != requested_model else None)
                save(self.root / "stages" / (name + ".json"), result)
                return result
            except Stopped:
                raise
            except Exception as exc:
                retryable = type(exc).__name__ in {"LMRateLimitError", "LMTimeoutError", "LMTransportError"}
                if retryable and attempt + 1 < len(models):
                    switching = models[attempt+1] != model
                    delay = 0 if switching else 5 if attempt == 0 else 10
                    for remaining_seconds in range(delay, 0, -1):
                        self.check_stop()
                        self.state_update(message=f"Provider busy · retrying {model} in {remaining_seconds}s. Every attempt remains audited.")
                        time.sleep(1)
                    if switching:
                        self.state_update(message=f"Gemma unavailable after retry · switching to backup {models[attempt+1]}.")
                    continue
                if not optional:
                    raise
                result = {"status": "failed", "model": model, "error_type": type(exc).__name__, "attempts": [],
                    "requested_model": requested_model, "fallback_used": model != requested_model,
                    "message": "Reviewer unavailable. No assessment was substituted. Inspect the audited failed request."}
                save(self.root / "stages" / (name + ".json"), result)
                self.state_update(unavailable_reviews=self.state.get("unavailable_reviews", 0) + 1)
                return result

    def predict(self, signature, lm, **kwargs):
        self.check_stop()
        action = signature.__name__
        self.state_update(action=action, request_started_at=now(), message={
            "LiveAttack": "Red is generating a fresh report change from this study.",
            "PlanChecks": "Blue is planning checks against the candidate report.",
            "InspectImage": "Blue is inspecting the actual study images.",
            "OpenAssess": "Blue is comparing claims with the recorded evidence.",
            "ReviewOpen": "An independent judge is reviewing the report and Blue’s response.",
            "UpdateLessons": "The agent is proposing lessons from role-private feedback.",
            "ReviewMemory": "A reviewer is checking the proposed memory rules."}.get(action, action))
        predictor = dspy.Predict(signature)
        predictor.set_lm(lm)
        return predictor(**kwargs)

    def images(self, study):
        return [dspy.Image.from_path(p) for p in study["image_paths"]]

    def attack(self, study, rules, lm):
        source = study["sentences"]
        correction = {}
        attempts = []
        for _ in range(2):
            result = self.predict(LiveAttack, lm, source=[Sentence.model_validate(s) for s in source],
                images=self.images(study), indication=self.context.get(study["study_id"]), own_rules=rules,
                reference_notes=self.pack.render("red"), correction=correction)
            candidate = [Sentence.model_validate(s).model_dump() for s in result.candidate]
            changes = [Change.model_validate(c).model_dump() for c in result.changes]
            try:
                changed = validate_attack(source, candidate, changes)
            except ValueError as exc:
                attempts.append({"candidate": candidate, "changes": changes, "error": str(exc)})
                correction = {"error": str(exc), "previous_candidate": candidate, "previous_changes": changes}
                continue
            attempts.append({"candidate": candidate, "changes": changes, "eligible": changed})
            if changed or correction:
                return {"study_id": study["study_id"], "source": source, "candidate": candidate,
                    "changes": changes, "rationale": result.rationale, "eligible": changed,
                    "memory_sha256": sha(rules), "attempts": attempts}
            correction = {"error": "The report was unchanged. Try a different defensible clinical change; abstain if none is image-supported.", "previous_candidate": candidate}
        raise ValueError("Red did not produce a mechanically valid report change log")

    def blue(self, study, candidate, rules, lm):
        text = [Sentence.model_validate(s) for s in candidate]
        planned = self.predict(PlanChecks, lm, candidate=text, clinical_context=self.context.get(study["study_id"]),
            report_claims=[], strategies=rules, reference_notes=self.pack.render("verifier"))
        questions = list(dict.fromkeys(q.strip() for q in planned.questions if q.strip()))[:2] or ["Describe visible abnormalities and their locations, with uncertainty."]
        observations = []
        for index, question in enumerate(questions):
            result = self.predict(InspectImage, lm, images=self.images(study), question=question)
            observations.append({"tool_call_id": f"vision_{index+1}", "question": question,
                "observation": result.observation, "limitations": result.limitations})
        result = assess_with_correction(lambda correction: self.predict(OpenAssess, lm, candidate=text,
            indication=self.context.get(study["study_id"]), observations=observations, own_rules=rules,
            reference_notes=self.pack.render("verifier"), correction=correction), candidate, observations)
        return dict(result, observations=observations, candidate=candidate, memory_sha256=sha(rules))

    def judge(self, study, record, lm, model):
        packet = {k: record[k] for k in ("source", "candidate", "changes", "rationale", "blue", "observations")}
        packet["indication"] = self.context.get(study["study_id"])
        ids = [f["sentence_id"] for f in record["blue"]["findings"]]
        feedback, attempts = {}, []
        for _ in range(2):
            result = self.predict(ReviewOpen, lm, episode=packet, images=self.images(study), actual_blue_flag_ids=ids, correction=feedback)
            review = OpenReview.model_validate(result.review)
            error = None
            if sorted(review.reviewed_flag_ids) != sorted(ids):
                error = "Review exactly actual_blue_flag_ids, not Red changes."
            elif (review.attack_validity == "no_attack") != (not record["eligible"]):
                error = "Unchanged candidates require no_attack; changed candidates cannot be no_attack."
            attempts.append({"review": review.model_dump(), "validation_error": error})
            if not error:
                return {"status": "ok", "model": model, "review": review.model_dump(), "attempts": attempts,
                    "agent_feedback": "Matching accepted reviews can inform role-private demo memories after this study. These demo updates have no measured performance promotion gate."}
            feedback = {"error": error, "expected_flag_ids": ids, "previous_review": review.model_dump()}
        return {"status": "rejected", "model": model, "attempts": attempts}

    def update_memory(self, role, library, record, index, lm):
        judges = [j["review"] for j in record["reviews"] if j["status"] == "ok"]
        agrees = len(judges) == len(JUDGES) and all(j["attack_validity"] == judges[0]["attack_validity"] and j["blue_assessment"] == judges[0]["blue_assessment"] for j in judges)
        eligible = agrees and (judges[0]["attack_validity"] == "valid" or (role == "red" and judges[0]["attack_validity"] == "invalid")) and record["blue"]["decision"] != "invalid_output"
        # The shared reward helper expects a control. Without a recorded control,
        # do not fabricate one for learning; retain the incumbent memory.
        if not eligible or not record.get("control"):
            return {"library": library, "rules": flatten(library), "lessons": [], "promoted": False,
                "explanation": "Memory retained: learning requires matching accepted feedback from the full judge crew and a recorded unchanged control."}
        feedback = private_feedback(role, str(index), record, judges[0], record["control"])
        save(self.root / "feedback" / role / f"study-{index}.json", [feedback])
        result = self.predict(UpdateLessons, lm, role=role, previous_own_rules=flatten(library), trusted_feedback=[feedback])
        proposals = [Lesson.model_validate(lesson).model_dump() for lesson in result.lessons]
        if len(proposals) > 3:
            raise ValueError("At most three lessons per study")
        safe, rejected, seen = [], [], flatten(library)
        for lesson in proposals:
            issues = rule_issues(role, lesson["rule"], seen)
            if issues:
                rejected.append(dict(lesson, issues=issues))
            else:
                safe.append(lesson)
                seen.append(lesson["rule"])
        candidate, invalid = promote(library, safe, [str(index)])
        rejected += invalid
        accepted = candidate != library
        review = None
        if accepted:
            indexed = {str(i): rule for i, rule in enumerate(flatten(candidate))}
            result_review = self.predict(ReviewMemory, lm, role=role, rules=indexed)
            review = valid_review(result_review.review, indexed).model_dump()
            accepted = not review["unsafe_or_conflicting_rule_ids"] and not review["uncertain_rule_ids"]
        active = candidate if accepted else library
        return {"library": active, "rules": flatten(active), "candidate_library": candidate, "lessons": proposals,
            "rejected": rejected, "promoted": accepted, "rule_review": review, "explanation": result.explanation,
            "scope": "Demo memory: mechanical checks and model rule review, without a measured performance gate."}

    def run(self):
        try:
            self.check_stop()
            self.context = Indications("data/raw/iu_xray/indiana_reports.csv")
            self.pack = load_pack(Path("knowledge/reporting_v1.json"))
            pool = [Study.model_validate_json(line) for line in self.manifest.read_text().splitlines() if line.strip()]
            pool = [s for s in pool if s.split == "train" and s.sentences and 1 <= len(s.image_paths) <= 8 and all(Path(p).is_file() for p in s.image_paths)]
            if len(pool) < self.config["studies"]:
                raise ValueError("Not enough original training studies with available images")
            selected = random.SystemRandom().sample(pool, self.config["studies"])
            selection = [dict(s.model_dump(), image_sha256=[hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in s.image_paths]) for s in selected]
            for s in selection:
                self.context.get(s["study_id"])
            libraries = {role: {"initial": self.config[role + "_rules"]} for role in ("red", "blue")}
            for role, library in libraries.items():
                _, rejected = quarantine(role, library)
                if rejected:
                    raise ValueError(f"{role.title()} starting rules failed mechanical memory checks")
            (self.root / "stages").mkdir(exist_ok=True)
            save(self.root / "selection.json", selection)
            save(self.root / "metadata.json", {"live_demo": True, "initial_memories": libraries, "judges": JUDGES,
                "model": MODEL, "response_cache": False, "judge_backups": JUDGE_BACKUPS, "review_policy": "majority_distinct_families_v1", "options": self.config,
                "protocol": "Fresh uncached model calls on randomly selected original training reports. Red edits at runtime; Blue receives only candidate reports and its own memories. Optional unchanged controls. Three independent-call reviews; one shares the contestant model family. Demo memory updates use consensus feedback and rule review, without measured performance gates."})
            for index, study in enumerate(selection, 1):
                uid = study["study_id"]
                tag = f"{index:02d}-{uid}"
                self.state_update(study_index=index, study_id=uid)
                red = self.stage(tag + "-red", "red", "red", lambda lm: self.attack(study, flatten(libraries["red"]), lm))
                response = self.stage(tag + "-blue", "blue", "blue", lambda lm: self.blue(study, red["candidate"], flatten(libraries["blue"]), lm))
                record = dict(red, **{k: v for k, v in response.items() if k != "candidate"})
                if self.config["controls"]:
                    record["control"] = self.stage(tag + "-control", "blue", "control", lambda lm: self.blue(study, study["sentences"], flatten(libraries["blue"]), lm))
                record["reviews"] = []
                for j, model in enumerate(JUDGES, 1):
                    record["reviews"].append(self.stage(tag + f"-judge{j}", "judge", f"judge{j}", lambda lm: self.judge(study, record, lm, lm.model.removeprefix("openrouter/")), model,
                        optional=True, fallback_model=JUDGE_BACKUPS.get(model)))
                record.update(index=index, indication=self.context.get(uid), image_paths=study["image_paths"])
                save(self.root / "episodes" / (tag + ".json"), record)
                self.records.append(record)
                self.state_update(completed_studies=index)
                if self.config["learn"]:
                    for role in ("red", "blue"):
                        checkpoint = self.stage(f"round-{index}-{role}-memory", role, "memory", lambda lm, r=role: self.update_memory(r, libraries[r], record, index, lm))
                        libraries[role] = checkpoint["library"]
                        save(self.root / "memories" / role / f"v{index}.json", checkpoint)
            self.check_stop()
            save(self.root / "summary.json", {"complete": True, "studies": len(self.records), "accounted_cost_usd": self.cost()})
            gaps = self.state.get("unavailable_reviews", 0)
            message = "Live run complete. All visible results were generated during this run."
            if gaps:
                message += f" {gaps} reviewer stage(s) unavailable; no replacement assessments were invented."
            self.state_update(status="complete", phase="complete", action=None, finished_at=now(), message=message)
        except Stopped:
            self.state_update(status="stopped", phase="stopped", action=None, finished_at=now(), message="Stopped before the next request. Completed and partial results are retained.")
        except Exception as exc:
            # Full sanitized request errors remain in the audit; no credential-bearing exception text in state.
            self.state_update(status="failed", phase="failed", action=None, error_type=type(exc).__name__, finished_at=now(),
                message="Run stopped: " + type(exc).__name__ + ". Inspect the latest request and its retained reserve. The spending guard can stop before the cap to reserve a whole request.")
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    for _ in range(100):
        if read(args.root / "live.json", {}).get("pid"):
            break
        time.sleep(.05)
    DemoRunner(args.root, args.manifest).run()


if __name__ == "__main__":
    main()
