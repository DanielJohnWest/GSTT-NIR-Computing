from functions.pacs.push_dicom_to_pacs import interpret_store_status


class FakeStatus:
    def __init__(self, status_code):
        self.Status = status_code


def test_interpret_store_status_success():
    result = interpret_store_status(FakeStatus(0x0000))
    assert result['success'] is True
    assert '0x0000' in result['message']


def test_interpret_store_status_failure_code():
    result = interpret_store_status(FakeStatus(0xA700))
    assert result['success'] is False
    assert '0xa700' in result['message']


def test_interpret_store_status_none():
    result = interpret_store_status(None)
    assert result['success'] is False
    assert 'Connection failed' in result['message']
