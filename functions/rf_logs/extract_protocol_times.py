import os

def extract_protocol_times(input_folder, keep_locs_and_adjs):

    key_words = ['adj', 'localiser', 'localizer']
    break_point = "New History Entry"
    sequence_data = {}

    for file in os.listdir(input_folder):
        if '.log' in file and 'RFSWD' in file:
            input_file = f"{input_folder}/{file}"

            first_break = False
            chunks = []
            entries = []

            with open(input_file, "r") as f:
                chunk = []
                for line in f:
                    chunk.append(line)
                    if break_point in line:
                        if not first_break:
                            chunk = [line]
                            first_break = True
                        else:
                            chunks.append(chunk)
                            chunk = []
                if chunk:
                    chunks.append(chunk)

            for chunk in chunks:
                name = None
                time = None
                for line in chunk:
                    if 'Protocol Name' in line:
                        name = line.split(':')[-1].strip()
                        if not keep_locs_and_adjs:
                            if any(word in line.lower() for word in key_words):
                                name = None
                    if 'Total Measurement Time (MCIR)' in line:
                        time = line.split(':')[-1].strip()

                if name and time:
                    entries.append((name, time))

            if len(entries) != 0:
                sequence_data[file] = entries

    return sequence_data



