"""
Swarm Meeting - TNP v0.1 State Machine & Transition Rules Module
Genesis Architect: Ehsanullah Rahimi (Ehsan)
"""

from enum import Enum
from typing import Set, Tuple

class ContractState(str, Enum):
    PROPOSED = "PROPOSED"
    NEGOTIATING = "NEGOTIATING"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    ACCEPTED = "ACCEPTED"
    EXECUTING = "EXECUTING"
    DELIVERED = "DELIVERED"
    BREACHED = "BREACHED"
    DISPUTED = "DISPUTED"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"
    SETTLED = "SETTLED"

# Define valid state transitions (Current_State -> Allowed_Next_States)
VALID_TRANSITIONS: Tuple[Tuple[ContractState, ContractState], ...] = (
    # Pre-acceptance flows
    (ContractState.PROPOSED, ContractState.NEGOTIATING),
    (ContractState.PROPOSED, ContractState.ACCEPTED),
    (ContractState.PROPOSED, ContractState.EXPIRED),
    (ContractState.PROPOSED, ContractState.CANCELLED),
    
    (ContractState.NEGOTIATING, ContractState.NEGOTIATING),
    (ContractState.NEGOTIATING, ContractState.ACCEPTED),
    (ContractState.NEGOTIATING, ContractState.EXPIRED),
    (ContractState.NEGOTIATING, ContractState.CANCELLED),
    
    # Post-acceptance execution flow
    (ContractState.ACCEPTED, ContractState.EXECUTING),
    (ContractState.ACCEPTED, ContractState.BREACHED), # Timeout or breach post-accept
    
    (ContractState.EXECUTING, ContractState.DELIVERED),
    (ContractState.EXECUTING, ContractState.BREACHED),
    (ContractState.EXECUTING, ContractState.DISPUTED),
    
    (ContractState.DELIVERED, ContractState.VERIFIED),
    (ContractState.DELIVERED, ContractState.DISPUTED),
    
    (ContractState.BREACHED, ContractState.DISPUTED),
    (ContractState.BREACHED, ContractState.FAILED),
    
    (ContractState.DISPUTED, ContractState.RESOLVED),
    (ContractState.DISPUTED, ContractState.FAILED),
    
    (ContractState.RESOLVED, ContractState.SETTLED),
    (ContractState.RESOLVED, ContractState.FAILED),
    
    (ContractState.VERIFIED, ContractState.SETTLED),
)

def is_valid_transition(current_state: ContractState, next_state: ContractState) -> bool:
    """Checks if a state transition is permitted according to TNP v0.1 rules."""
    return (current_state, next_state) in VALID_TRANSITIONS
