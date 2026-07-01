import os
import time

import pydicom as pyd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from functions.spectroscopy.is_evelina_spectroscopy import is_evelina_spectroscopy
from functions.spectroscopy.classify_spectroscopy_series import classify_spectroscopy_series
from functions.spectroscopy.find_matching_pair import find_matching_pair
from functions.spectroscopy.build_secondary_capture_dataset import build_secondary_capture_dataset
from functions.tarquin.escape_filepath import escape_filepath
from functions.tarquin.run_tarquin import run_tarquin
from functions.pdf_manipulations.pdf_to_png import pdf_to_png
from functions.pacs.push_dicom_to_pacs import push_dicom_to_pacs


PACS_IP = "172.31.2.56"
PACS_PORT = 8062
PACS_AE_TITLE = "SCP_MINIMAC"

HOROS_PATH = "/Users/radiologyadmin/Documents/Horos Data/DATABASE.noindex/10000"
ARCHIVE_DIR = "./archive/"


def find_spec(runfilelist):
    """
    Looks at the most recently added file in runfilelist. If it's a valid
    Evelina ECC/ref spectroscopy file, checks whether its matching partner
    is already in runfilelist.

    Parameters
    ----------
    runfilelist : list of str
        Paths of DICOM files currently being tracked.

    Returns
    -------
    tuple
        (runfilelist, wsup_path, wref_path, source_dataset)
        wsup_path/wref_path/source_dataset are None if no complete pair
        was found (the newest file is then dropped from runfilelist, or
        left on it to wait for its partner - see comments below).
    """
    newest_path = runfilelist[-1]

    if not pyd.misc.is_dicom(newest_path):
        runfilelist.pop()
        return runfilelist, None, None, None

    ds = pyd.dcmread(newest_path)

    if not is_evelina_spectroscopy(ds):
        runfilelist.pop()
        return runfilelist, None, None, None

    series_description = getattr(ds, 'SeriesDescription', None)
    classification = classify_spectroscopy_series(series_description)

    if classification is None:
        runfilelist.pop()
        return runfilelist, None, None, None

    study_uid = getattr(ds, 'StudyInstanceUID', 'No Study Instance')

    candidates = [
        {'path': path, 'dataset': pyd.dcmread(path)}
        for path in runfilelist
    ]

    match = find_matching_pair(candidates, classification['partner_description'], study_uid)

    if match is None:
        # partner not in yet - leave the newest file on the list and wait
        return runfilelist, None, None, None

    runfilelist.remove(match['path'])
    runfilelist.remove(newest_path)

    if classification['kind'] == 'ecc':
        wsup_path, wref_path = newest_path, match['path']
    else:
        wsup_path, wref_path = match['path'], newest_path

    return runfilelist, wsup_path, wref_path, ds


def output_n_clear(ds):
    """
    Runs tarquin's output PDF through the archive pipeline: converts it to
    a PNG, embeds it as PixelData in a Secondary Capture DICOM, and saves
    both the PDF and DICOM to the archive directory.

    Parameters
    ----------
    ds : pydicom.Dataset
        The source dataset (the _ECC or _ref file) used for header info.

    Returns
    -------
    str
        Path to the saved DICOM file (to be pushed to PACS).
    """
    png_bytes = pdf_to_png('temp.pdf')
    ds2 = build_secondary_capture_dataset(ds, png_bytes)

    dicom_path = os.path.join(ARCHIVE_DIR, f'{ds2.PatientID}_{ds2.SeriesDescription}.dcm')
    ds2.save_as(dicom_path, write_like_original=False)

    pdf_path = os.path.join(ARCHIVE_DIR, f'{ds2.PatientID}_{ds2.SeriesDescription}.pdf')
    os.rename('temp.pdf', pdf_path)

    return dicom_path


def pmain(runfilelist):
    """
    Runs one full cycle: find a matched pair (if any), process it through
    tarquin, archive the result, and push it to PACS.
    """
    runfilelist, wsup_path, wref_path, ds = find_spec(runfilelist)

    if wsup_path is None:
        return runfilelist

    wsup_escaped = escape_filepath(wsup_path)
    wref_escaped = escape_filepath(wref_path)

    run_tarquin(wsup_escaped, wref_escaped)
    dicom_path = output_n_clear(ds)
    push_dicom_to_pacs(dicom_path, PACS_IP, PACS_PORT, PACS_AE_TITLE)

    return runfilelist


class MyHandler(FileSystemEventHandler):
    def __init__(self):
        self.runfilelist = self._init_runfilelist()

    @staticmethod
    def _init_runfilelist():
        seed_file = os.path.join(HOROS_PATH, '2.dcm')
        if not os.path.exists(seed_file):
            print(f'{seed_file} not found please change code for a file that exists')
            raise SystemExit(1)
        print('running file list created')
        return [seed_file]

    def on_created(self, event):
        print(f"Created: {event.src_path}")
        self.runfilelist.append(event.src_path)
        self.runfilelist = pmain(self.runfilelist)


def main():
    handler = MyHandler()
    observer = Observer()
    observer.schedule(handler, HOROS_PATH, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        observer.join()


if __name__ == '__main__':
    main()
