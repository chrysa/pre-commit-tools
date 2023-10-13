#!/usr/bin/env bash
set -euo pipefail

output_html=''
output_json=''


args=$(getopt -a -o h:j: --long output-html:,output-json: -- "$@")

eval set -- ${args}
while $@; do
    case $1 in
        -h | --output-html) output_html="$OPTARG"; shit ;;
        -j | --output-json) output_json="$OPTARG"; shit ;;
    esac
done

echo $@
echo $1
pylint $@
pylint --output-format=pylint_report.CustomJsonReporter--load-plugins=pylint_report  $@ >  $output_json
pylint-report $output_json -o $output_html
