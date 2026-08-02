.PHONY: quality-gate-baseline quality-gate-verify

quality-gate-baseline: ## Record baseline metrics for regression detection
	@quality-gate-baseline

quality-gate-verify: ## Verify no regression since baseline
	@quality-gate-verify
