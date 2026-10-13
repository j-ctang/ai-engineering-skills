import subprocess
import tempfile
import unittest
from pathlib import Path

from check_dco import unsigned


class UnsignedTest(unittest.TestCase):
    """Run the check against a real repo, so git's trailer parsing is covered."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.dir.name)
        self.git("init", "-q")
        self.base = self.commit("base", "a@x")

    def tearDown(self):
        self.dir.cleanup()

    def git(self, *args, email="a@x"):
        return subprocess.run(
            [
                "git",
                "-c",
                "user.name=A",
                "-c",
                f"user.email={email}",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=self.repo,
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def commit(self, message, email):
        self.git("commit", "-q", "--allow-empty", "-m", message, email=email)
        return self.git("rev-parse", "HEAD").strip()

    def test_signed_by_author_passes(self):
        head = self.commit("- Change\n\nSigned-off-by: A <a@x>", "a@x")
        self.assertEqual(unsigned(self.repo, self.base, head), [])

    def test_missing_sign_off_fails(self):
        head = self.commit("- Change", "a@x")
        self.assertEqual(unsigned(self.repo, self.base, head), [(head, "a@x")])

    def test_sign_off_by_someone_else_fails(self):
        head = self.commit("- Change\n\nSigned-off-by: B <b@x>", "a@x")
        self.assertEqual(unsigned(self.repo, self.base, head), [(head, "a@x")])

    def test_sign_off_in_body_text_is_not_a_trailer(self):
        head = self.commit("- Change\n\nSigned-off-by: A <a@x>\n\nMore text.", "a@x")
        self.assertEqual(unsigned(self.repo, self.base, head), [(head, "a@x")])

    def test_bot_commits_are_exempt(self):
        head = self.commit("- Bump", "49699333+dependabot[bot]@users.noreply.github.com")
        self.assertEqual(unsigned(self.repo, self.base, head), [])

    def test_merge_commits_are_skipped(self):
        self.git("switch", "-q", "-c", "side")
        side = self.commit("- Side\n\nSigned-off-by: A <a@x>", "a@x")
        self.git("switch", "-q", "-")
        self.commit("- Main\n\nSigned-off-by: A <a@x>", "a@x")
        self.git("merge", "-q", "--no-ff", "--no-edit", side)
        head = self.git("rev-parse", "HEAD").strip()
        self.assertEqual(unsigned(self.repo, self.base, head), [])


if __name__ == "__main__":
    unittest.main()
