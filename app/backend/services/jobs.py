#!/usr/bin/env python3
"""
비동기 Job 레지스트리 (U9).

보고서 생성은 PS2 진행률 UX(web_design_spec §5.3, 5종 프로그레스바)와 맞추기 위해
비동기로 실행하고 진행 상태를 폴링한다(B2 결정). 데모 규모라 인메모리 dict 로 충분
(A1: 파일시스템·무DB). 멀티프로세스 배포 시에는 외부 저장소 필요 — U23 메모.

5단계(PS2): 시장 / 규제 / 상품 / 시스템 / 결과 생성.
job_id 발급은 외부 randomness 없이 단조 카운터 + 대상코드 조합.
"""

import threading

# PS2 5단계 정의 (web_design_spec §PS2)
STEPS = [
    {"key": "market", "label": "시장"},
    {"key": "regulation", "label": "규제"},
    {"key": "product", "label": "상품"},
    {"key": "system", "label": "시스템"},
    {"key": "result", "label": "결과 생성"},
]
STEP_KEYS = [s["key"] for s in STEPS]

_lock = threading.Lock()
_jobs = {}
_counter = 0


def _new_job_id(kind, code):
    global _counter
    with _lock:
        _counter += 1
        return f"job_{kind}_{code}_{_counter:04d}"


def create_job(kind, code):
    """새 job 등록. 모든 단계 pending 으로 초기화."""
    job_id = _new_job_id(kind, code)
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "kind": kind,
            "code": code,
            "status": "pending",      # pending | running | done | error
            "progress": 0,            # 0~100
            "steps": [{**s, "state": "pending"} for s in STEPS],
            "report_id": None,
            "error": None,
        }
    return job_id


def _recompute_progress(job):
    done = sum(1 for s in job["steps"] if s["state"] == "done")
    job["progress"] = round(done / len(job["steps"]) * 100)


def start_step(job_id, step_key):
    with _lock:
        job = _jobs[job_id]
        job["status"] = "running"
        for s in job["steps"]:
            if s["key"] == step_key:
                s["state"] = "running"


def finish_step(job_id, step_key):
    with _lock:
        job = _jobs[job_id]
        for s in job["steps"]:
            if s["key"] == step_key:
                s["state"] = "done"
        _recompute_progress(job)


def complete(job_id, report_id):
    with _lock:
        job = _jobs[job_id]
        job["status"] = "done"
        job["report_id"] = report_id
        job["progress"] = 100
        for s in job["steps"]:
            s["state"] = "done"


def fail(job_id, message):
    with _lock:
        job = _jobs.get(job_id)
        if job:
            job["status"] = "error"
            job["error"] = message
            # 진행 중이던 단계를 error 로
            for s in job["steps"]:
                if s["state"] == "running":
                    s["state"] = "error"


def get_job(job_id):
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None


def reset():
    """테스트용 — 레지스트리 초기화."""
    global _counter
    with _lock:
        _jobs.clear()
        _counter = 0
