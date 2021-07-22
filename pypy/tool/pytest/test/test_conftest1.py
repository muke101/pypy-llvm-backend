
import py

innertest = py.path.local(__file__).dirpath('conftest1_innertest.py')
pytest_plugins = "pytester"

class TestPyPyTests:
    def test_selection_by_keyword_interp(self, testdir):
        sorter = testdir.inline_run("-m", "interplevel", innertest, )
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 2, len(passed)
        assert not skipped and not failed
        assert "test_something" in passed[0].nodeid
        assert "test_method" in passed[1].nodeid

    def test_selection_by_keyword_app(self, testdir):
        sorter = testdir.inline_run("-m", "applevel", innertest)
        passed, skipped, failed = sorter.listoutcomes()
        assert len(passed) == 1
        assert not skipped and not failed
        assert "test_method_app" in passed[0].nodeid
