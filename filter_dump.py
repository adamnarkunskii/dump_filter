import re
import sys
import argparse

interesting_labels = ["_start", "recaller", "main", "foo", "bar"]

label_pattern = re.compile(r"^(\w+) <(\w+)>:$")
instruction_pattern = re.compile(r"\s*\w+:\s*(\w+).*")
jump_exit_pattern = re.compile(r"\s*\w+:\s*\w+\s+j\s+\w+\s+<exit>")

NOP = "00000013"
J_WAT = "0000006f"

MAXIMUM_PER_LINE = "0xEFF"

MAX_ADD_INSTRUCTION = "EFF70713"
ADD_INSTRUCTION = "%s70713"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--offset', default=0, type=int, help='amount (in decimal) to add to the program\'s sp')
    parser.add_argument('--files', nargs='+')
    args = parser.parse_args(sys.argv[1:])
    file_names = args.files

    prologue = calculate_sp_adds(args.offset)

    for filename in file_names:
        with open(filename, 'r') as f:
            with open(filename + '.filtered', 'w') as out_f:
                main_loop(f, out_f, prologue[::-1])


def calculate_sp_adds(offset):
    adds = []
    if offset:
        number_of_max_adds = offset / int(MAXIMUM_PER_LINE, 16)
        remainder_add = offset % int(MAXIMUM_PER_LINE, 16)

        if number_of_max_adds > 4:
            raise Exception("offset is too large!")

        adds = [MAX_ADD_INSTRUCTION] * number_of_max_adds
        adds.append(ADD_INSTRUCTION % hex(remainder_add)[2:].upper())

    nops = [NOP] * (5 - len(adds))

    adds.extend(nops)

    return adds


def main_loop(in_file, out_file, prologue):
    printing = False
    nop_countdown = -1
    nop_count = 0
    for line in in_file:
        m = label_pattern.search(line)
        if m:  # this is a label
            label = m.group(2)
            if label in interesting_labels:
                printing = True
                location_shifted = hex((int(m.group(1), 16) - 0xe000) / 4)[2:]
                line = "@%s\n" % location_shifted
                if label == "_start":
                    nop_countdown = 4

            if label not in interesting_labels:
                printing = False
        else:  # check if this is an instruction line
            m = instruction_pattern.search(line)
            if m:
                j_match = jump_exit_pattern.search(line)
                if j_match:
                    line = "%s\n" % J_WAT
                else:
                    line = "%s\n" % m.group(1)

            else:  # garbage line, put it where it belongs
                line = None

        # write out the line
        if printing and line:
            if nop_countdown > 0:
                nop_countdown -= 1
            if nop_countdown == 0:
                nop_countdown = -1
                nop_count = 5
            if nop_count > 0:
                line = "%s\n" % prologue.pop()
                nop_count -= 1
            out_file.write(line)


if __name__ == '__main__':
    main()
