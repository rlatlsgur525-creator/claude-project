"""check_draft.py 회귀 테스트.

사용 (naver-blog 폴더에서, 컴퓨터에 따라 python3 대신 python):
  python3 -m unittest tools/test_check_draft.py -v

실제 초안과 tools/tests/fixtures/ 의 고정 문서로, 등급(필수/권고)과 종료 코드가 바뀌지 않았는지 본다.
v1.5 검사기의 결과는 tools/tests/baseline_v1.5_checker.txt 에 남아 있다 (비교용).
"""
import subprocess, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "tools" / "check_draft.py"
FIX = ROOT / "tools" / "tests" / "fixtures"


def run(draft, *args):
    p = subprocess.run([sys.executable, str(SCRIPT), str(draft), *args], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    return p.returncode, p.stdout


def failed(out):
    return [l.strip()[3:] for l in out.splitlines() if l.strip().startswith("실패 ")]


class RealDrafts(unittest.TestCase):
    def test_v23_draft_mode_passes_must(self):
        code, out = run(ROOT / "15_draft_fire_insurance_v2.3.md")
        self.assertEqual(code, 0, out)
        self.assertIn("[사람 확인]", out)

    def test_v23_publish_blocked_by_blanks_only(self):
        # 2026-10-27 사실 검증 완료 뒤: 빈칸·이미지 자리표시로만 막힌다 (미확인 차단은 test_publish_unverified_fact_fails)
        code, out = run(ROOT / "15_draft_fire_insurance_v2.3.md", "--publish")
        self.assertEqual(code, 1)
        f = " ".join(failed(out))
        self.assertIn("빈칸", f)
        self.assertNotIn("사실 검증표", f)
        self.assertIn("이미지 자리표시", f)

    def test_virtual_scenario_blocked_on_publish(self):
        code, out = run(ROOT / "17_review_drafts" / "A_storybrand.md", "--publish")
        self.assertEqual(code, 1)
        self.assertIn("가상 시나리오 아님", " ".join(failed(out)))

    def test_commercial_link_is_must(self):
        code, out = run(ROOT / "07_draft_fire_insurance.md")
        self.assertEqual(code, 1)
        self.assertIn("상업 링크", " ".join(failed(out)))

    def test_keyword_metadata_mismatch_is_must(self):
        code, out = run(ROOT / "10_sim" / "sim05_AC_penalty.md")
        self.assertEqual(code, 1)
        self.assertIn("메인 검색어가 제목이나 본문에 있음", " ".join(failed(out)))

    def test_same_opening_as_previous_post_is_must(self):
        code, out = run(ROOT / "15_draft_fire_insurance_v2.3.md", "--prev", str(ROOT / "15_draft_fire_insurance_v2.2.md"))
        self.assertEqual(code, 1)
        self.assertIn("첫 문장 앞 6자", " ".join(failed(out)))

    def test_short_simulation_is_advisory_not_failure(self):
        # v1.5에서는 분량·소제목 형식만으로 실패했던 글 (baseline 참고)
        code, out = run(ROOT / "10_sim" / "sim02_C_place_photo.md")
        self.assertEqual(code, 0, out)
        self.assertIn("권고 분량", out)


class Fixtures(unittest.TestCase):
    def test_experiment_type_relaxes_headings(self):
        code, out = run(FIX / "experiment_short.md")
        self.assertEqual(code, 0, out)
        self.assertIn("정보 번호 질문형 소제목", out)
        self.assertIn("권고 분량", out)

    def test_banned_phrase_fails(self):
        code, out = run(FIX / "banned_phrase.md")
        self.assertEqual(code, 1)
        self.assertIn("상투어 없음", " ".join(failed(out)))

    def test_publish_ready_passes(self):
        code, out = run(FIX / "publish_ready.md", "--publish")
        self.assertEqual(code, 0, out)
        self.assertIn("발행 전 사람 확인으로", out)

    def test_publish_unverified_fact_fails(self):
        code, out = run(FIX / "publish_unverified.md", "--publish")
        self.assertEqual(code, 1)
        self.assertIn("T2(미확인)", out)

    def test_unverified_fact_is_only_info_in_draft_mode(self):
        code, out = run(FIX / "publish_unverified.md")
        self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
