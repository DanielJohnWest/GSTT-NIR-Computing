import pydicom as pyd


def build_secondary_capture_dataset(source_ds, png_bytes):
    """
    Parameters
    ----------
    source_ds : pydicom.Dataset
        The original DICOM dataset (the _ECC or _ref file) used to pull
        patient/study identifiers from.
    png_bytes : bytes
        Raw RGB pixel bytes of the rendered Tarquin PDF page.

    Returns
    -------
    pydicom.Dataset
        A fully populated Secondary Capture dataset with PixelData set,
        ready to be saved with ds2.save_as(...).
    """
    file_meta = pyd.Dataset()
    unique_uid = pyd.uid.generate_uid()

    elements_to_define_meta = {
        'FileMetaInformationGroupLength': 210,
        'MediaStorageSOPClassUID': '1.2.840.10008.5.1.4.1.1.7',
        'ImplementationVersionName': 'alantest ',
        'MediaStorageSOPInstanceUID': unique_uid,
    }
    elements_to_transfer_meta = {
        'ImplementationClassUID': 'ImplementationClassUID',
        'FileMetaInformationVersion': 'FileMetaInformationVersion',
        'TransferSyntaxUID': 'TransferSyntaxUID',
    }

    for key, value in elements_to_define_meta.items():
        setattr(file_meta, key, value)

    for key, source_attr in elements_to_transfer_meta.items():
        try:
            setattr(file_meta, key, getattr(source_ds.file_meta, source_attr))
        except AttributeError:
            pass

    elements_to_define = {
        'Format': 'DICOM',
        'FormatVersion': 3,
        'Width': 2337,
        'Height': 1653,
        'BitDepth': 3,
        'ColorType': 'truecolor',
        'SOPClassUID': '1.2.840.10008.5.1.4.1.1.7',
        'Modality': 'MR',
        'ConversionType': 'WSD',
        'TimeOfSecondaryCapture': '',
        'SecondaryCaptureDeviceManufacturer': 'Tarquin',
        'SecondaryCaptureDeviceManufacturerModelName': '4.3.11',
        'SecondaryCaptureDeviceSoftwareVersion': '4.3.11',
        'SOPInstanceUID': unique_uid,
        'SeriesInstanceUID': pyd.uid.generate_uid(),
        'SeriesNumber': 456 + source_ds.SeriesNumber,
        'InstanceNumber': 1,
        'SamplesPerPixel': 3,
        'PhotometricInterpretation': 'RGB',
        'PlanarConfiguration': 0,
        'Rows': 1653,
        'Columns': 2337,
        'BitsAllocated': 8,
        'BitsStored': 8,
        'HighBit': 7,
        'PixelRepresentation': 0,
        'LossyImageCompression': '00',
    }

    elements_to_transfer = {
        'SpecificCharacterSet': 'SpecificCharacterSet',
        'StudyDate': 'StudyDate',
        'SeriesDate': 'SeriesDate',
        'AcquisitionDate': 'StudyDate',
        'StudyTime': 'StudyTime',
        'AcquisitionTime': 'StudyTime',
        'AccessionNumber': 'AccessionNumber',
        'PatientID': 'PatientID',
        'PatientBirthDate': 'PatientBirthDate',
        'PatientSex': 'PatientSex',
        'DateOfSecondaryCapture': 'StudyDate',
        'StudyInstanceUID': 'StudyInstanceUID',
        'StudyID': 'StudyID',
        'PerformedProcedureStepDescription': 'PerformedProcedureStepDescription',
        'ReferringPhysicianName': 'ReferringPhysicianName',
        'PatientName': 'PatientName',
    }

    if source_ds.data_element('StudyDescription') is not None:
        elements_to_transfer['StudyDescription'] = 'StudyDescription'

    if source_ds.data_element('SeriesDescription') is not None:
        elements_to_define['SeriesDescription'] = 'Tarquin_' + source_ds.SeriesDescription
        elements_to_define['ProtocolName'] = 'Tarquin_' + source_ds.SeriesDescription
    else:
        elements_to_define['SeriesDescription'] = 'Tarquin'
        elements_to_define['ProtocolName'] = 'Tarquin'

    ds2 = pyd.Dataset()
    ds2.file_meta = file_meta
    ds2.is_implicit_VR = False
    ds2.is_little_endian = True

    for key, value in elements_to_define.items():
        setattr(ds2, key, value)

    for key, source_attr in elements_to_transfer.items():
        setattr(ds2, key, getattr(source_ds, source_attr))

    setattr(ds2, 'PixelData', png_bytes)

    return ds2
