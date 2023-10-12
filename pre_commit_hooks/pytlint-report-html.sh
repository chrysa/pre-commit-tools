#!/usr/bin/env bash
set -e

pylint $@ > report.json
