#!/usr/bin/python3
import os
import pathlib
import shutil
import sys


def compress_warm_start_directory(output_path, scenario_name):
    cwd = os.getcwd()
    os.chdir(str(output_path.parent))
    warm_start_name = scenario_name + "__warm-start"
    warm_start_zip_name = shutil.make_archive(warm_start_name, 'zip', str(output_path))
    os.chdir(cwd)
    return warm_start_zip_name


def _replace_bau_file(fixed_data_root_path, source, bau_root_handle, dest_name=None):
    dest_name = dest_name if dest_name else source.name
    destination = fixed_data_root_path / "sf_light" / "bau" / bau_root_handle / dest_name
    print(str(destination))

    if destination.exists():
        destination.unlink()
    source.replace(destination)


def move_and_replace_bau_files(output_path, fixed_data_root_path):
    iters_dir = (output_path / 'ITERS').iterdir()
    max_iter_with_linkstats, linkstats_file = find_largest_iteration_with_linkstats(iters_dir)

    scenario_name = output_path.name.split("__")[0]
    warm_start_zip_path = pathlib.Path(compress_warm_start_directory(output_path, scenario_name))
    sample_name = warm_start_zip_path.name.split("__")[0].split("-", maxsplit=1)[1]

    # _replace_bau_file(fixed_data_root_path, warm_start_zip_path, "warm-start")
    stats_source = output_path / "summaryStats.csv"

    stats_name = f"summaryStats-{sample_name}.csv"
    _replace_bau_file(fixed_data_root_path, stats_source, "stats", stats_name)

    dest_name = f"linkstats_bau-{sample_name}.csv.gz"

    _replace_bau_file(fixed_data_root_path, linkstats_file, "linkstats", dest_name)


def find_largest_iteration_with_linkstats(iters_dir):
    iters_dir = list(iters_dir)
    max_iter_with_linkstats = 1
    max_path_with_linkstats = iters_dir[0]
    for iter_path in iters_dir[1:]:
        iter_num = int(iter_path.name.strip('it.'))
        linkstats_path = (iter_path / f"{iter_num}.linkstats.csv.gz")
        if linkstats_path.exists() and iter_num > max_iter_with_linkstats:
            shutil.rmtree(str(max_path_with_linkstats.absolute()))
            max_iter_with_linkstats = iter_num
            max_path_with_linkstats = iter_path
        else:
            shutil.rmtree(str(iter_path.absolute()))

    return max_iter_with_linkstats, (max_path_with_linkstats / f"{max_iter_with_linkstats}.linkstats.csv.gz")


def main(beam_output_dir, fixed_data_root):
    output_path = pathlib.Path(beam_output_dir)
    fixed_data_root_path = pathlib.Path(fixed_data_root)

    move_and_replace_bau_files(output_path, fixed_data_root_path)
    shutil.rmtree(beam_output_dir)


if __name__ == '__main__':
    beam_output_dir = sys.argv[1]
    fixed_data_root = sys.argv[2]
    main(beam_output_dir, fixed_data_root)
