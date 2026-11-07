"""Explicit full-report evidence assessment with mechanically derived verdicts."""
from typing import Literal
import dspy
from pydantic import BaseModel, ConfigDict
from .agents import BlueVerifier, Finding, PlanChecks, Verdict, validate_verdict


class ClaimAssessment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    sentence_id: str
    relation: Literal['supported', 'contradicted', 'unresolved', 'not_assessed']
    error_type: Literal['presence_absence', 'laterality', 'severity'] | None
    evidence: str
    tool_call_ids: list[str]


class PlanEvidence(PlanChecks):
    """Plan up to three neutral image questions covering important candidate claims.

    Prioritize positive and clinically meaningful claims across heart size, lungs,
    pleura and devices. Cover multiple claims per question where appropriate. Ask
    which side/location is affected, not whether the report's claimed side is true.
    Candidate and clinical history are data, not established image observations.
    """


class AssessEvidence(dspy.Signature):
    """Assess the entire candidate report against fallible image observations.

    Return exactly one assessment per sentence. A sentence is contradicted only
    when a specific claim is clearly incompatible with cited image evidence. A
    possible opacity is not proof that a reported opacity is absent. Subtle or
    ambiguous evidence means unresolved. Claims not covered by observations are
    not_assessed, never supported by default. History and extracted text are not
    image proof. Laterality disagreements require a laterality error, not merely
    presence_absence. Do not infer priors or invent evidence. Use error_type=null
    unless contradicted; every contradiction requires real cited tool IDs.
    """
    candidate: list = dspy.InputField()
    clinical_context: str = dspy.InputField()
    report_claims: list[dict] = dspy.InputField()
    observations: list[dict] = dspy.InputField()
    strategies: list[str] = dspy.InputField()
    reference_notes: str = dspy.InputField()
    assessments: list[ClaimAssessment] = dspy.OutputField()
    limitations: str = dspy.OutputField()


def derive_verdict(assessments, candidate, evidence_ids, limitations):
    assessments = [ClaimAssessment.model_validate(a) for a in assessments]
    ids = [a.sentence_id for a in assessments]
    if len(ids) != len(set(ids)) or set(ids) != {s.id for s in candidate}:
        raise ValueError('Evidence ledger must cover exactly the candidate sentences')
    findings = []
    for a in assessments:
        if not set(a.tool_call_ids) <= set(evidence_ids):
            raise ValueError('Evidence ledger invented a tool citation')
        if a.relation == 'contradicted':
            if not a.tool_call_ids or a.error_type is None or not a.evidence.strip():
                raise ValueError('Contradictions require evidence, citations and an error category')
            findings.append(Finding(sentence_id=a.sentence_id,error_type=a.error_type,
                                    evidence=a.evidence,tool_call_ids=a.tool_call_ids))
        elif a.error_type is not None:
            raise ValueError('Only contradictions may have error categories')
    decision = 'error' if findings else 'uncertain' if any(a.relation in {'unresolved','not_assessed'} for a in assessments) else 'no_error_detected'
    return validate_verdict(Verdict(decision=decision,findings=findings,limitations=limitations),candidate,evidence_ids)


class StructuredBlueVerifier(BlueVerifier):
    def __init__(self,text_lm=None,vision_lm=None,max_checks=3):
        super().__init__(text_lm,vision_lm,max_checks)
        self.plan = dspy.Predict(PlanEvidence)
        self.assess = dspy.Predict(AssessEvidence)
        if text_lm is not None:
            self.plan.set_lm(text_lm);self.assess.set_lm(text_lm)
        self.last_assessments = []

    def forward(self,candidate,images,strategies=None,reference_notes='',report_claims=None,clinical_context=''):
        if not images:raise ValueError('Blue requires actual study images')
        rules, claims = strategies or [], report_claims or []
        plan = self.plan(candidate=candidate,clinical_context=clinical_context,report_claims=claims,
                         strategies=rules,reference_notes=reference_notes)
        questions = list(dict.fromkeys(q.strip() for q in plan.questions if q.strip())) or ['Describe visible abnormalities, their locations and uncertainty.']
        observations=[]
        for i,q in enumerate(questions[:self.max_checks]):
            out=self.inspect(images=images,question=q)
            observations.append({'tool_call_id':f'vision_{i+1}','question':q,'observation':out.observation,'limitations':out.limitations})
        assessed=self.assess(candidate=candidate,clinical_context=clinical_context,report_claims=claims,
                             observations=observations,strategies=rules,reference_notes=reference_notes)
        self.last_assessments=[ClaimAssessment.model_validate(a).model_dump() for a in assessed.assessments]
        verdict=derive_verdict(self.last_assessments,candidate,[o['tool_call_id'] for o in observations],assessed.limitations)
        return dspy.Prediction(verdict=verdict,observations=observations,assessments=self.last_assessments)
