"""
Decodes and encodes binary files used by the Malvern Omnisec SEC/GPC system
Decodes to csv
encodes csv to binary
"""
import csv  # for csv reading and writing
import glob  # for reading files with certain file extensions
import struct  # for converting binary to float
import time  # for timing
from itertools import zip_longest  # for transposing data series of different lengths


def menu(title, items, prompt):
    table_length_min = len(title)  # minimum width accounts for header title
    table_lengths = [len(str(len(items))), max([len(item) for item in items]), 5]
    if table_lengths[1] < table_length_min:
        table_lengths[1] = table_length_min

    # Print the list of items in a nice table
    print(f'\n| {"I":<{table_lengths[0]}} | {title:<{table_lengths[1]}}')
    print(f'{"-" * sum(table_lengths)}')
    for i, name in enumerate(items):
        print(f'| {i:<{table_lengths[0]}} | {name}')
    print(f'{"-" * sum(table_lengths)}')

    n = 0
    while True:
        n += 1
        if n > 4:
            print('Honestly!? I give up.')  # message to be printed if the user sucks at life
            exit(0)
        try:
            choice_number = input(prompt)
            choice_number = int(choice_number)
            if choice_number == int(len(items)) - 1:
                print('Sorry for the inconvenience. Goodbye.')
                exit(0)
            elif choice_number in range(len(items)):
                choice_item = items[choice_number]
                break
            else:
                print(f'Why would you chose that? {choice_number} is not an option.')
        except ValueError:
            print(f'Why would you chose that? {choice_number} is not an integer.')

    return choice_item


def decodeomnisec(file_in, file_out):
    start_total = time.perf_counter()  # record start time of calculation

    # open the binary file chosen by the user
    # Max file size this should ever have to deal with is ~50 MB so opening the whole file at once is fine
    start_read_decode = time.perf_counter()  # record start time of reading and decoding
    with open(file_in, 'rb') as encoded_file:
        file_reference_position = 0  # set the initial file reference

        header = struct.unpack(header_structure[0], encoded_file.read(header_structure[1]))  # read the file header
        file_reference_position += header_structure[1]  # change the file reference position by specific number of bytes
        encoded_file.seek(file_reference_position)  # move the file reference position

        # get the number of data series from the file header
        data_series_amount = int(header[3])

        # read the data headers. Looped according to the number of data series specified
        data_header = []  # list to put all the raw hexadecimal in
        data_series_lengths = []  # list to record the length of each data series in
        for n in range(data_series_amount):
            data_header.append(struct.unpack(data_header_structure[0],
                                             encoded_file.read(data_header_structure[1])))  # read the data headers
            data_series_lengths.append(int(data_header[n][2] / 4))  # length of each data series in bytes
            file_reference_position += data_header_structure[1]  # change the file reference position
            encoded_file.seek(file_reference_position)  # move the file reference position

        # read the data series. looped for the amount of them.
        # also is sized for each individual series
        data_series = []
        for n in range(data_series_amount):
            data_series.append(struct.unpack(f'{int(data_series_lengths[n])}{data_series_structure[0]}',
                                             encoded_file.read(int(data_series_structure[1] * data_series_lengths[
                                                 n]))))  # read the data headers
            file_reference_position += int(data_series_structure[1] * data_series_lengths[n])
            encoded_file.seek(file_reference_position)  # move the file reference position

    end_read_decode = time.perf_counter()  # record the final time for reading and decoding
    print(f'Decoding time: {round(end_read_decode - start_read_decode, 4)} seconds')

    # write the decoded data to a csv file
    start_csv_write = time.perf_counter()

    with open(f'{file_out}', 'w') as csv_file:
        # add check so that files are not overwritten. do this earlier so that the program doesn't exit after most of the work is done
        header = list(header)  # convert header tuple to list
        for i in 0, 1:  # decode text so that it doesn't look dumb
            header[i] = header[i].decode('ascii').rstrip('\x00')
        csv.writer(csv_file).writerow(header)  # write header

        data_header = [list(series) for series in data_header]  # convert data header tuples to lists
        for series in data_header:
            series[0] = series[0].decode('ascii').rstrip('\x00')
        data_header = zip_longest(*data_header)  # transpose the list
        csv.writer(csv_file).writerows(data_header)

        data_series = zip_longest(*data_series)
        csv.writer(csv_file).writerows(data_series)

    # record the time for writing the csv, and inform the user
    end_csv_write = time.perf_counter()
    print(f'csv write time: {round(end_csv_write - start_csv_write, 4)} seconds')

    # record the total calculation time of the script
    end_total = time.perf_counter()
    print(f'csv written as: {file_out}')
    print(f'Total calculation time: {round(end_total - start_total, 4)} seconds')


def encodeomnisec(file_in, file_out):
    start_total = time.perf_counter()  # record start time of calculation

    start_read = time.perf_counter()  # record start time of reading
    # the csv file is read in parts and cleaned up as it goes.
    # this is done to prevent any issues in getting values from the header and data headers
    with open(file_in, 'r') as csv_file:  # open the csv file chosen by the user
        csv_reader = csv.reader(csv_file)  # set up csv reader so its easy to use
        header = [item for item in next(csv_reader) if item]  # read the header and only add non-empty strings
        header = [item.replace('\ufeff', '') for item in header]  # remove \ufeff that is added by excel
        for i, item in enumerate(header):  # everything is imported as a string. Convert to proper type here
            if any(c.isalpha() for c in item):
                header[i] = item.encode('utf-8')  # make anything that contains letters a string
            else:
                header[i] = int(item)  # make all other items an integer (only other option in the header)

        data_header = []  # read all the data headers
        for i in range(data_header_structure[2]):  # index two of the data header structure contains the number of items in the data headers
            data_header.append([item for item in next(csv_reader) if item])  # add all non-empty strings to a sublist
        for n, item in enumerate(data_header):
            for i, name in enumerate(item):  # Same as above. Convert strings to byte strings and integers
                if any(c.isalpha() for c in name):
                    data_header[n][i] = name.encode('utf-8')
                else:
                    data_header[n][i] = int(name)
        data_series_lengths = [int(num / 4) for num in data_header[2]]
        data_header = list(zip_longest(*data_header))

        data_series = []
        for i in range(max(data_series_lengths)):
            data_series.append(next(csv_reader))
        data_series = list(zip_longest(*data_series))
        data_series = [float(item) for sublist in data_series for item in sublist if item]
        data_series_lengths_sum = sum(data_series_lengths)
    end_read = time.perf_counter()
    print(f'csv read time: {round(end_read - start_read, 4)} seconds')

    # perform consistency checks here
    # make sure there are as many data series as there are supposed to be
    if not len(data_header) == header[3]:
        print('Error, incorrect number of data series')
        exit(0)
    # compare the length of the data series with how long they are supposed to be
    if not data_series_lengths_sum == len(data_series):
        print('Error, incorrect length of data series')
        exit(0)

    start_write = time. perf_counter()  # record start time of byte file writing
    with open(file_out, 'wb') as byte_file:
        byte_file.write(struct.pack(header_structure[0], *header))
        for item in data_header:
            byte_file.write(struct.pack(data_header_structure[0], *item))
        byte_file.write(struct.pack(f'{data_series_lengths_sum}{data_series_structure[0]}', *data_series))

    end_write = time.perf_counter()
    print(f'Omnisec byte file write time: {round(end_write - start_write, 4)} seconds')

    end_total = time.perf_counter()
    print(f'file written as: {file_out}')
    print(f'Total calculation time: {round(end_total - start_total, 4)} seconds')


function_options = ('Decode Omnisec files to csv', 'Encode csv to Omnisec files', 'Exit')  # program functions
# takes the function choice and assigns it to a function keyword
function_options_parameters = {
    'Decode Omnisec files to csv': ('decode'),
    'Encode csv to Omnisec files': ('encode')
}

# dictionary of recognized extensions for Malvern Omnisec files that can be decoded and encoded
extensions = {
    'decode': ('chrome_flt', 'chrome_uflt', 'chromeuvd', 'chromeenv', 'noise', 'chromeanalysis', 'out'),
    'encode': ('csv', '')
}  # the extra blank item is here to make the for in bit below behave. Without it treats the extensions as c, s, and v

function_choice = menu('Program functions', function_options, 'Enter the number corresponding to the function you wish to use: ')
function_choice = function_options_parameters[function_choice]
# print list of files to be decoded or encoded
# at this point what was chosen doesn't matter except for what files will be displayed
# Add files that have the appropriate extension to a list and add an exit option
file_list = []
for ext in extensions[function_choice]:
    # file_list.extend(glob.glob(f'/Users/npaisley/Google Drive/Kovalenko/rawData/gpc/dataExports/*.{ext}'))  # for general use
    file_list.extend(glob.glob(f'testingData/*.{ext}'))  # for testing within pycharm
file_list.append('Never mind')

file_to_convert = menu('File name', file_list, f'Enter the number corresponding to the file you wish to {function_choice}: ')
print('\nConverting...')

# list that defines the structure of each part of the binary file.
header_structure = ('16s 32s 2i', 56)  # 16 bytes string, 32 bytes string, two integers
data_header_structure = ('32s 5i', 52, 6)  # 32 byte string, five integers, number of total items
data_series_structure = ('f', 4)  # each data point is a float

# do a check here for existing files to avoid overwrite
# if file_to_convert in file_list and function_choice == 'decode':
#     print(f'Warning! There is already a csv file corresponding to {file_to_convert}')
#     print('Please rename, move, or delete the csv file to proceed')
#     exit(0)
# incorporate an existing file check here
if function_choice == 'encode':
    # print('\nSorry, this function is not available yet')
    encodeomnisec(file_to_convert, f'{file_to_convert}.out')
    exit(0)
elif function_choice == 'decode':  # could name output csv file here
    decodeomnisec(file_to_convert, f'{file_to_convert}.csv')
    exit(0)

exit(0)
