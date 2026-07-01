"""
push_dicom_to_pacs
---------------------
Pushes a DICOM file to a PACS storage node via a C-STORE request.

The network association itself can't meaningfully be unit tested without a
real PACS endpoint, but the status-interpretation logic is pulled out into
interpret_store_status() below so it can be tested independently with a
fake status object.
"""

import pydicom as pyd
from pynetdicom import AE, StoragePresentationContexts


def interpret_store_status(status):
    """
    Parameters
    ----------
    status : pydicom.Dataset-like or None
        The status object returned by assoc.send_c_store(). Must have a
        .Status attribute if not None.

    Returns
    -------
    dict
        {'success': bool, 'message': str}
    """
    if status is None:
        return {'success': False, 'message': 'Connection failed to do the sending'}

    success = status.Status == 0x0000
    message = f"C-STORE request status: 0x{status.Status:04x}"
    return {'success': success, 'message': message}


def push_dicom_to_pacs(path, ip_address, port, ae_title, requested_context="1.2.840.10008.1.1"):
    """
    Parameters
    ----------
    path : str
        Path to the DICOM file to push.
    ip_address : str
        PACS storage node IP address.
    port : int
        PACS storage node port.
    ae_title : str
        Called AE title of the storage node.
    requested_context : str, default "1.2.840.10008.1.1"
        SOP Class UID to request as a presentation context.

    Returns
    -------
    dict
        {'success': bool, 'message': str}
    """
    ae = AE()
    ae.add_requested_context(requested_context)

    ds = pyd.dcmread(path)

    assoc = ae.associate(ip_address, port, StoragePresentationContexts, ae_title=ae_title)

    if not assoc.is_established:
        return {'success': False, 'message': 'Association failed, was rejected or aborted'}

    status = assoc.send_c_store(ds)
    result = interpret_store_status(status)
    assoc.release()

    return result
