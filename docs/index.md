# pylongfellow

::: pylongfellow
    options:
      members: false
      show_root_heading: false
      show_root_toc_entry: false

## Differential testing

Two independent implementations of the same proof system back one interface, and the test
suite uses that: the differential tests exchange proofs over every (prover backend, verifier
backend) pair, across the committed v6 and v7 circuits at one to four attributes, plus the
proofs in zk-cred-longfellow's test vectors. The full suite, differential tests included,
gates every wheel build. A nightly canary builds both backends from their upstreams' HEADs
and runs the same suite. Divergences are recorded in
[`tests/differential/README.md`](https://github.com/pipe23-org/pylongfellow/blob/main/tests/differential/README.md).
