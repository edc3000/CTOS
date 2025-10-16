#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lottery with factor weights + tamper-evident audit chain (blockchain-style).
- One-file implementation, stdlib only.
- Config: JSON (weights, participants, draw options).
- Output:
  1) winners CSV
  2) audit_chain.jsonl (append-only hash chain)
- Verify mode: checks the audit chain integrity and (if files still exist) re-hashes to confirm.
"""

import argparse
import hashlib
import json
import math
import os
import sys
import csv
import uuid
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Tuple

# ---------- Utils ----------

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha256_file(path: str) -> str:
    with open(path, "rb") as f:
        return sha256_bytes(f.read())

def canonical_json_bytes(obj: Any) -> bytes:
    """Deterministic JSON bytes for hashing (sorted keys, no spaces)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# ---------- Audit chain (append-only hash chain) ----------

class AuditChain:
    """
    Very lightweight blockchain-like audit log:
    - JSONL file where each line is a 'block' with fields:
      index, timestamp, action, draw_id, payload, prev_hash, hash
    - 'hash' = SHA256 over the canonical JSON of the block WITHOUT the trailing 'hash'.
    - Each block includes 'prev_hash' to chain integrity.
    - You can append multiple draws into the same audit file.
    """
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
        self._index, self._prev_hash = self._load_tail()

    def _load_tail(self) -> Tuple[int, str]:
        if not os.path.exists(self.path) or os.path.getsize(self.path) == 0:
            return 0, "0" * 64
        idx = 0
        prev_hash = "0" * 64
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                blk = json.loads(line)
                idx = blk.get("index", idx)
                prev_hash = blk.get("hash", prev_hash)
        return idx, prev_hash

    def add_block(self, action: str, draw_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        block = {
            "index": self._index + 1,
            "timestamp": utc_now_iso(),
            "action": action,
            "draw_id": draw_id,
            "payload": payload,
            "prev_hash": self._prev_hash,
        }
        # Compute hash without including 'hash' itself
        block_no_hash = json.loads(json.dumps(block, sort_keys=True, separators=(",", ":")))
        block_hash = sha256_bytes(canonical_json_bytes(block_no_hash))
        block["hash"] = block_hash

        # Persist
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(block, ensure_ascii=False) + "\n")

        # Advance the tail
        self._index += 1
        self._prev_hash = block_hash
        return block

    @staticmethod
    def verify(path: str) -> bool:
        """Verify the entire chain file."""
        if not os.path.exists(path):
            print(f"[verify] audit file not found: {path}")
            return False
        prev_hash = "0" * 64
        expected_index = 1
        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    blk = json.loads(line)
                except Exception as e:
                    print(f"[verify] JSON parse error at line {line_no}: {e}")
                    return False

                if blk.get("index") != expected_index:
                    print(f"[verify] index mismatch at line {line_no}: got {blk.get('index')} expected {expected_index}")
                    return False
                if blk.get("prev_hash") != prev_hash:
                    print(f"[verify] prev_hash mismatch at line {line_no}")
                    return False

                # Recompute hash
                blk_copy = blk.copy()
                blk_hash = blk_copy.pop("hash", None)
                recomputed = sha256_bytes(canonical_json_bytes(json.loads(json.dumps(blk_copy, sort_keys=True, separators=(",", ":")))))
                if blk_hash != recomputed:
                    print(f"[verify] hash mismatch at line {line_no}")
                    return False

                prev_hash = blk_hash
                expected_index += 1

        print("[verify] OK: chain structure valid.")
        return True

# ---------- Config loading & canonicalization ----------

def load_and_canonicalize_config(path: str) -> Tuple[Dict[str, Any], bytes, str]:
    raw_text = read_text(path)
    try:
        cfg = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"[error] Invalid JSON in config: {e}")
        sys.exit(2)

    # Basic validation
    if "draw" not in cfg or "factors" not in cfg or "participants" not in cfg:
        print("[error] config must contain 'draw', 'factors', 'participants'.")
        sys.exit(2)
    if not isinstance(cfg["factors"], dict):
        print("[error] 'factors' must be an object {factor: weight}.")
        sys.exit(2)
    for k, v in cfg["factors"].items():
        if v < 0:
            print(f"[error] factor '{k}' has negative weight.")
            sys.exit(2)

    # Sort participants by id for canonical hashing (order-independent)
    parts = cfg.get("participants", [])
    ids = [p.get("id") for p in parts]
    if len(ids) != len(set(ids)):
        print("[error] duplicate participant id found.")
        sys.exit(2)
    parts_sorted = sorted(parts, key=lambda x: x.get("id", ""))

    # Build a canonical snapshot for hashing (sorted keys)
    canonical_obj = {
        "version": cfg.get("version", 1),
        "draw": cfg["draw"],
        "factors": dict(sorted(cfg["factors"].items(), key=lambda kv: kv[0])),
        "participants": parts_sorted
    }
    canon_bytes = canonical_json_bytes(canonical_obj)
    return cfg, canon_bytes, sha256_bytes(canon_bytes)

# ---------- Seed derivation ----------

def derive_seed(cfg_canon_bytes: bytes, draw_cfg: Dict[str, Any]) -> Tuple[int, str, str]:
    """
    Returns (seed_int, mode_used, seed_note)
    - deterministic: seed = sha256( cfg_canon + manual_seed + external_entropy )
    - system: seed = sha256( cfg_canon + os_random_32bytes )
    """
    mode = draw_cfg.get("seed_mode", "deterministic").lower()
    manual_seed = str(draw_cfg.get("manual_seed", ""))
    external_entropy = str(draw_cfg.get("external_entropy", ""))

    if mode not in ("deterministic", "system"):
        mode = "deterministic"

    if mode == "deterministic":
        mix = cfg_canon_bytes + manual_seed.encode("utf-8") + external_entropy.encode("utf-8")
        seed_hex = sha256_bytes(mix)
        seed_int = int(seed_hex, 16) & ((1 << 64) - 1)  # fit into 64 bits for Random
        note = f"deterministic (manual_seed='{manual_seed}', external_entropy='{external_entropy}')"
        return seed_int, mode, note
    else:
        os_bytes = os.urandom(32)
        mix = cfg_canon_bytes + os_bytes
        seed_hex = sha256_bytes(mix)
        seed_int = int(seed_hex, 16) & ((1 << 64) - 1)
        note = "system (seed derived from os.urandom; recorded for reproducibility)"
        return seed_int, mode, note

# ---------- Weighting & sampling ----------

def build_weights(cfg: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns (positives, zeros) where each item is:
      {"id": str, "weight": float, "factors": List[str]}
    Participants with unknown factors simply ignore those factors (weight += 0).
    """
    factor_w: Dict[str, float] = cfg["factors"]
    positives, zeros = [], []
    for p in cfg["participants"]:
        pid = p["id"]
        seq = p.get("factors", [])
        w = 0.0
        for f in seq:
            w += factor_w.get(f, 0.0)  # unknown factors contribute 0
        item = {"id": pid, "weight": float(w), "factors": seq}
        if w > 0.0:
            positives.append(item)
        else:
            zeros.append(item)
    return positives, zeros

def weighted_sample_without_replacement(rng, items: List[Dict[str, Any]], k: int) -> List[Tuple[str, float, float]]:
    """
    Efraimidis–Spirakis (A-ExpJ) via exponential keys:
    For each item with weight w>0, draw u~U(0,1), score = -ln(u)/w. Pick k smallest scores.
    Returns list of tuples (id, weight, score).
    """
    scored = []
    for it in items:
        w = it["weight"]
        # numeric guard
        if w <= 0:
            continue
        u = rng.random()
        while u == 0.0:  # avoid ln(0)
            u = rng.random()
        score = -math.log(u) / w
        scored.append((it["id"], w, score))
    # sort by ascending score (smaller = higher priority)
    scored.sort(key=lambda t: t[2])
    return scored[:k]

# ---------- Winners file ----------

def save_winners_csv(path: str, winners: List[Tuple[str, float, float]]):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "participant_id", "weight", "score"])
        for i, (pid, w, score) in enumerate(winners, 1):
            writer.writerow([i, pid, f"{w:.12g}", f"{score:.12g}"])

# ---------- Main draw ----------

def do_draw(config_path: str, winners_out: str, audit_path: str):
    # Load config and canonical hash
    cfg, canon_bytes, cfg_hash = load_and_canonicalize_config(config_path)

    draw_cfg = cfg["draw"]
    requested_k = int(draw_cfg.get("num_winners", 1))
    if requested_k <= 0:
        print("[error] num_winners must be >= 1")
        sys.exit(2)

    # Prepare audit chain & draw id
    chain = AuditChain(audit_path)
    draw_id = str(uuid.uuid4())

    # Hash current code file for auditing
    try:
        code_hash = sha256_file(os.path.abspath(__file__))
    except Exception:
        code_hash = "<unavailable>"

    # GENESIS block
    chain.add_block(
        "GENESIS",
        draw_id,
        {
            "config_path": os.path.abspath(config_path),
            "config_hash": cfg_hash,
            "code_path": os.path.abspath(__file__),
            "code_hash": code_hash,
            "python_version": sys.version
        }
    )

    # Derive seed & build RNG
    seed_int, seed_mode, seed_note = derive_seed(canon_bytes, draw_cfg)
    rng = __import__("random").Random(seed_int)
    chain.add_block(
        "RNG_SEED",
        draw_id,
        {
            "seed_mode": seed_mode,
            "seed_note": seed_note,
            "seed_int": seed_int  # recording exact seed enables reproduction
        }
    )

    # Build weights
    positives, zeros = build_weights(cfg)
    if not positives and not zeros:
        print("[error] no participants.")
        sys.exit(2)

    # Weighted sampling (positives) + fallback fill from zeros if needed
    k_from_pos = min(requested_k, len(positives))
    pos_selected = weighted_sample_without_replacement(rng, positives, k_from_pos)

    winners: List[Tuple[str, float, float]] = list(pos_selected)

    if len(winners) < requested_k and len(zeros) > 0:
        need = requested_k - len(winners)
        # Uniform from zeros (weights are zero): use random scores only for ordering
        zeros_scored = []
        for it in zeros:
            u = rng.random()
            score = -math.log(u) if u > 0 else float("inf")
            zeros_scored.append((it["id"], 0.0, score))
        zeros_scored.sort(key=lambda t: t[2])
        winners.extend(zeros_scored[:need])

    # DRAW block: record full candidate table (compressed)
    record_full_table = False
    all_pos = None
    if record_full_table:
        tmp = weighted_sample_without_replacement(rng=__import__("random").Random(seed_int), items=positives, k=len(positives))
        all_pos = [{"id": pid, "weight": w, "score": s} for (pid, w, s) in tmp]

    chain.add_block(
        "DRAW",
        draw_id,
        {
            "requested_winners": requested_k,
            "positives_count": len(positives),
            "zeros_count": len(zeros),
            "winners": [{"id": pid, "weight": w, "score": s} for (pid, w, s) in winners],
            "all_positive_scored": all_pos  # or None
        }
    )

    # Save winners file
    save_winners_csv(winners_out, winners)
    winners_hash = sha256_file(winners_out)
    chain.add_block(
        "WINNERS_SAVED",
        draw_id,
        {
            "winners_out": os.path.abspath(winners_out),
            "winners_hash": winners_hash
        }
    )

    # Final echo
    print(f"[done] winners saved to: {winners_out}")
    print(f"[done] audit chain appended: {audit_path}")
    print(f"[note] last block hash (anchor this in git/tweet for immutability): {chain._prev_hash}")

# ---------- Verify mode ----------

def do_verify(audit_path: str):
    ok = AuditChain.verify(audit_path)
    if not ok:
        sys.exit(1)
    with open(audit_path, "r", encoding="utf-8") as f:
        blocks = [json.loads(x) for x in f if x.strip()]
    if not blocks:
        return
    last = blocks[-1]
    payload = last.get("payload", {})
    winners_out = payload.get("winners_out")
    winners_hash = payload.get("winners_hash")
    if winners_out and winners_hash and os.path.exists(winners_out):
        curr = sha256_file(winners_out)
        if curr == winners_hash:
            print("[verify] winners file hash matches the chain record.")
        else:
            print("[verify] WARNING: winners file hash mismatch.")


def _load_blocks(audit_path: str):
    if not os.path.exists(audit_path):
        print(f"[verify-config] audit file not found: {audit_path}")
        return []
    with open(audit_path, "r", encoding="utf-8") as f:
        return [json.loads(x) for x in f if x.strip()]

def verify_with_config(audit_path: str, config_path: str):
    # 1) chain structure
    if not AuditChain.verify(audit_path):
        sys.exit(1)

    blocks = _load_blocks(audit_path)
    if not blocks:
        print("[verify-config] empty audit chain.")
        sys.exit(1)

    # 2) target draw: the last block's draw_id
    target_draw = blocks[-1].get("draw_id")
    if not target_draw:
        print("[verify-config] cannot locate target draw_id from last block.")
        sys.exit(1)

    # 3) locate GENESIS of this draw to get recorded config_hash
    recorded_cfg_hash = None
    for b in blocks:
        if b.get("draw_id") == target_draw and b.get("action") == "GENESIS":
            recorded_cfg_hash = b.get("payload", {}).get("config_hash")
    if not recorded_cfg_hash:
        print("[verify-config] cannot find GENESIS/config_hash for the target draw.")
        sys.exit(1)

    # 4) compute current config canonical hash
    try:
        _, canon_bytes, curr_cfg_hash = load_and_canonicalize_config(config_path)
    except SystemExit:
        raise
    except Exception as e:
        print(f"[verify-config] failed to load config: {e}")
        sys.exit(1)

    print(f"[verify-config] recorded config_hash: {recorded_cfg_hash}")
    print(f"[verify-config] current   config_hash: {curr_cfg_hash}")
    if curr_cfg_hash == recorded_cfg_hash:
        print("[verify-config] OK: provided config.json matches the recorded hash for the latest draw.")
        sys.exit(0)
    else:
        print("[verify-config] MISMATCH: provided config.json does NOT match the recorded config for the latest draw.")
        sys.exit(2)

# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Weighted lottery with blockchain-style audit.")
    ap.add_argument("--verify-config", help="verify that a given config.json matches the latest draw in the audit chain", default=None)
    ap.add_argument("--config", help="path to config.json", required=False)
    ap.add_argument("--winners-out", help="output CSV path", default="winners.csv")
    ap.add_argument("--audit-chain", help="audit JSONL path", default="audit_chain.jsonl")
    ap.add_argument("--verify", help="verify the audit chain file (no draw)", action="store_true")
    args = ap.parse_args()

    if args.verify:
        do_verify(args.audit_chain)
    elif args.verify_config:
        verify_with_config(args.audit_chain, args.verify_config)
    else:
        if not args.config:
            print("Usage: lottery.py --config config.json [--winners-out winners.csv] [--audit-chain audit_chain.jsonl]")
            sys.exit(2)
        do_draw(args.config, args.winners_out, args.audit_chain)

if __name__ == "__main__":
    main()
