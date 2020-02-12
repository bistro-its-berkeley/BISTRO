#!/usr/bin/python3
import os
import pathlib
import shutil
import sys


def compress_output_directory(output_path, target_dir, scenario_name, linkstats_file):
    cwd = os.getcwd()
    os.chdir(str(output_path.parent))
    target_data_name = "{}-__output_data".format(scenario_name)
    target_data_path = target_dir / pathlib.Path(target_data_name)
    shutil.copy(str(linkstats_file), str(output_path))
    warm_start_zip_name = shutil.make_archive(target_data_path, 'zip', str(output_path))
    os.chdir(cwd)
    return warm_start_zip_name


def clean_and_move_output_files(output_path, target_dir_path):
    iters_dir = (output_path / 'ITERS').iterdir()
    linkstats_file = find_largest_iteration_with_linkstats(iters_dir)
    scenario_name = output_path.name.split("__")[0]
    return pathlib.Path(compress_output_directory(output_path, target_dir_path, scenario_name, linkstats_file))


def find_largest_iteration_with_linkstats(iters_dir):
    iters_dir = list(iters_dir)
    max_iter_with_linkstats = 1
    max_path_with_linkstats = iters_dir[0]
    for iter_path in iters_dir[1:]:
        iter_num = int(iter_path.name.strip('it.'))
        linkstats_path = (iter_path / "{}.linkstats.csv.gz".format(iter_num))
        if linkstats_path.exists() and iter_num > max_iter_with_linkstats:
            shutil.rmtree(str(max_path_with_linkstats.absolute()))
            max_iter_with_linkstats = iter_num
            max_path_with_linkstats = iter_path
        else:
            shutil.rmtree(str(iter_path.absolute()))

    return max_path_with_linkstats / "{}.linkstats.csv.gz".format(max_iter_with_linkstats)


def main(beam_output_dir, target_dir):
    output_dir_path = pathlib.Path(beam_output_dir)
    target_dir_path = pathlib.Path(target_dir)
    clean_and_move_output_files(output_dir_path, target_dir_path)
    shutil.rmtree(beam_output_dir)


if __name__ == '__main__':
    beam_output_dir = sys.argv[1]
    target_dir = sys.argv[2]
    main(beam_output_dir, target_dir)
