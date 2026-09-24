"""In-memory, single-use permit authority bound to action content."""

from .models import ActionProposal, ControlDecision, DecisionOutcome, ExecutionPermit


class PermitError(PermissionError):
    pass


class ExecutionPermitAuthority:
    def __init__(self) -> None:
        self._issued: dict[str, tuple[str, str, str, DecisionOutcome, str]] = {}

    def issue(
        self,
        proposal: ActionProposal,
        decision: ControlDecision,
        approval_source: str,
    ) -> ExecutionPermit:
        if decision.action_id != proposal.action_id:
            raise PermitError("decision does not match the action")
        if decision.proposal_digest != proposal.digest():
            raise PermitError("decision does not match the action contents")
        if (
            decision.outcome == DecisionOutcome.ALLOW
            and decision.source == "jev"
            and approval_source == "jev"
        ):
            approved = True
        elif (
            decision.outcome == DecisionOutcome.REVIEW
            and approval_source == "caller"
            and decision.source == "caller"
        ):
            approved = True
        else:
            raise PermitError("only an allowed decision or explicit caller approval can issue a permit")

        permit = ExecutionPermit(
            action_id=proposal.action_id,
            tool=proposal.tool,
            decision=decision.outcome,
            approved=approved,
            approval_source=approval_source,
            proposal_digest=proposal.digest(),
        )
        self._issued[permit.permit_id] = (
            proposal.action_id,
            proposal.digest(),
            proposal.tool,
            decision.outcome,
            approval_source,
        )
        return permit

    def consume(self, proposal: ActionProposal, permit: ExecutionPermit | None) -> None:
        if permit is None:
            raise PermitError("an execution permit is required")
        if not permit.approved:
            raise PermitError("execution permit is not approved")
        issued = self._issued.get(permit.permit_id)
        expected = (
            proposal.action_id,
            proposal.digest(),
            proposal.tool,
            permit.decision,
            permit.approval_source,
        )
        if (
            issued is None
            or issued != expected
            or permit.action_id != proposal.action_id
            or permit.tool != proposal.tool
            or permit.proposal_digest != proposal.digest()
        ):
            raise PermitError("permit is invalid or does not match this action")
        del self._issued[permit.permit_id]

    def revoke(self, permit: ExecutionPermit) -> None:
        """Discard a permit when a final policy recheck changes the outcome."""
        self._issued.pop(permit.permit_id, None)
