"""
Swarm Meeting - TNP v0.1 Cryptography & Canonicalization Module
Genesis Architect: Ehsanullah Rahimi (Ehsan)
"""

import base64
import json
from nacl.signing import SigningKey, VerifyKey
from nacl.exceptions import BadSignatureError

def canonicalize_json(data: dict) -> bytes:
    """
    Produces deterministic canonical JSON bytes following strict formatting rules.
    Ensures keys are sorted and whitespace is stripped to prevent signature mismatch.
    """
    # Standardizing sorting and removing unnecessary spaces
    canonical_str = json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
    return canonical_str.encode('utf-8')

def sign_payload(signing_key: SigningKey, payload: dict) -> str:
    """
    Signs the canonicalized byte representation of a dictionary payload.
    Returns base64-encoded Ed25519 signature.
    """
    canonical_bytes = canonicalize_json(payload)
    signed = signing_key.sign(canonical_bytes)
    return base64.b64encode(signed.signature).decode('utf-8')

def verify_signature(pubkey_hex: str, payload: dict, signature_b64: str) -> bool:
    """
    Verifies an Ed25519 signature against the canonicalized payload.
    """
    try:
        verify_key = VerifyKey(bytes.fromhex(pubkey_hex))
        canonical_bytes = canonicalize_json(payload)
        sig_bytes = base64.b64decode(signature_b64.encode('utf-8'))
        verify_key.verify(canonical_bytes, sig_bytes)
        return True
    except (BadSignatureError, ValueError, Exception):
        return False
