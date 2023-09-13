#!/bin/bash

# To enable this hook, rename this file to "pre_commit".

###############################################################################
# https://gist.github.com/stuntgoat/8800170
# Git pre_commit hook for finding and warning about Python print
# statements.
#

# Set this to 0 to turn off testing.
TESTING=0
ALL_FILES=false

function display() {
    if [ ${TESTING} == 1 ]; then
        echo $1
    fi
}

display "get head revision"
# Get the current git HEAD
head=$(git rev-parse --verify HEAD)

display "define regex"
# BSD regex for finding Python print statements
find_print='print[[:space:](]*'

display "search print"
# Save output to $out var
if [ ${ALL_FILES} == true ]; then
    out=$(find ${PWD} -type f -name '*.py' -and -not -path "*build*" -exec cat {} \; | grep -e ${find_print})
else
    out=$(git diff ${head} -- '*.py' | grep -e ${find_print})
fi
# Count number of prints
count=$(echo "${out}" | grep -e '\w' | wc -l)
if [ $count -gt 0 ]; then
    echo
    echo "###############################################################################"
    echo "$out"
    echo "###############################################################################"
    echo "       " $count "print statement(s) found in commit!"
    echo
    echo "  Abort : <enter>"
    echo "  Commit: commit <enter>"
    echo
    echo ">>> \c"

    ## Get stdin from a keyboard:
    ## http://stackoverflow.com/a/10015707
    exec </dev/tty

    # Let user type option.
    read command

    ## Close stdin.
    exec <&-

    # Lower input received
    lowered=$(echo ${command} | tr '[:upper:]' '[:lower:]')

    if [ "$command" = "commit" ]; then
        echo "committing print statement(s)"
        exit $TESTING
    fi
    echo "aborting"
    exit 1
fi
