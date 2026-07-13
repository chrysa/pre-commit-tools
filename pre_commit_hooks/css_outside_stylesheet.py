#!/usr/bin/python3
"""Hook to detect CSS written outside of CSS/SCSS files (CSS-in-JS)."""

from __future__ import annotations

import re
from collections.abc import Sequence

from pre_commit_hooks.tools.pattern_detection import PatternDetection


def main(argv: Sequence[str] | None = None) -> int:
    """Detect CSS-in-JS carriers in non-stylesheet files and return 1 if any found.

    Flags the common ways CSS leaks into JS/TS/JSX/TSX/HTML/Vue sources instead of
    living in a dedicated ``.css``/``.scss`` file:

    - styled-components / emotion tagged templates
      (``styled.div`` `` ` ``, ``styled(Comp)`` `` ` ``, ``css`` `` ` ``,
      ``createGlobalStyle`` `` ` ``, ``keyframes`` `` ` ``, ``injectGlobal`` `` ` ``)
    - inline ``<style>`` blocks embedded in markup.
    """
    pattern_detection = PatternDetection(
        commented=re.compile(r'^\s*(?://|<!--|\*|/\*)'),
        disable_comment=re.compile(r'css-outside-stylesheet\s*:\s*disable'),
        pattern=re.compile(
            r'(?:\bstyled\s*(?:\.\w+|\([^`]*\))'
            r'|\b(?:createGlobalStyle|keyframes|injectGlobal|css)\s*)`'
            r'|<style[\s>]',
        ),
    )
    return pattern_detection.detect(
        argv=argv,
        help_msg='detect CSS written outside CSS/SCSS files (CSS-in-JS)',
    )


if __name__ == '__main__':
    raise SystemExit(main())
