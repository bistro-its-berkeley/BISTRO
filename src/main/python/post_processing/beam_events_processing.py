# -*- coding: utf-8 -*-
import argparse
from pathlib import Path

import boto3

from fixed_data_visualization import ResultFiles, ReferenceData

BUCKET_NAME = 'uber-prize-testing-output'


def process_events(path_output_folder, iter_number, sample_size):
    ref = ReferenceData(sample_size)
    ResultFiles(path_output_folder, iter_number, ref)


def remote_path(args):
    if "random_search_num" in args:
        return "search-input/Exploration_{}/{}/output/".format(args.random_search_num, args.s3_dest_key)
    else:
        return "fixed-input/{}/output/".format(args.s3_dest_key)


# 3. upload results to s3
def upload_results(output_folder, s3_dest_key):
    s3api = boto3.resource('s3')

    for f in Path(output_folder).iterdir():
        if 'dataframe' in f.name:
            print("Uploading: {}".format({f.name}))
            resp = s3api.Object(BUCKET_NAME, s3_dest_key + f.name).put(Body=open(str(f), 'rb'))
            if resp['ResponseMetadata']['HTTPStatusCode'] != 200:
                raise ConnectionError('Bad request, response:\n {0}'.format(str(resp)))
            else:
                print("Successfully uploaded {0} to s3://{1}".format(f.name, BUCKET_NAME + '/' + s3_dest_key + f.name))


def run(args):
    output_path = Path(args.output_dir)
    process_events(output_path, args.iter_number, args.sample_size)
    upload_results(output_path, remote_path(args))
    print("Done uploading post-processed data!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Post-processing utilities that can be executed after completion of a BISTRO visualization.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--output_dir", type=str, help="Path to output directory.")
    parser.add_argument("--iter_number", type=str, help="Iteration used to parse data.")
    parser.add_argument("--sample_size", type=str, default="15k", help="Sample size.")
    # parser.add_argument("--random_search_num", type=int, required=False)
    # parser.add_argument('--s3_dest_key', type=str, required=True)
    args = parser.parse_args()

    run(args)
