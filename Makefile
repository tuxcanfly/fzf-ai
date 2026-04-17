.PHONY: install install-pip install-symlink clean test help

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: install-py  ## Install using pip (recommended)

install-pip:  ## Install using pip
	pip install .

install-symlink:  ## Install by symlinking to ~/.local/bin (traditional method)
	@mkdir -p ~/.local/bin
	@for script in bin/fzf-ai bin/fzf-ai-index bin/fzf-ai-preview bin/fzf-ai-resume bin/fzf-ai-ui; do \
		if [ -f "$$script" ]; then \
			echo "Linking $$script to ~/.local/bin/"; \
			ln -sf "$$(pwd)/$$script" ~/.local/bin/; \
		else \
			echo "Warning: $$script not found"; \
		fi; \
	done
	@echo "Make sure ~/.local/bin is in your PATH"
	@echo "export PATH=\"$$HOME/.local/bin:$$PATH\""

install-py:  ## Install Python scripts to system
	@echo "Installing Python scripts..."
	python3 -c "import sys; sys.path.insert(0, '.'); import bin.fzf-ai-index, bin.fzf-ai-preview"
	@echo "Python scripts can be executed directly from bin/ directory"

test:  ## Run basic tests
	@echo "Testing basic functionality..."
	@cd bin && ./fzf-ai-index --help >/dev/null 2>&1 || echo "fzf-ai-index test failed"
	@cd bin && ./fzf-ai-preview --help >/dev/null 2>&1 || echo "fzf-ai-preview test failed"
	@echo "Basic tests completed"

clean:  ## Clean up installation
	@echo "Removing symlinks..."
	@for script in fzf-ai fzf-ai-index fzf-ai-preview fzf-ai-resume fzf-ai-ui; do \
		if [ -L "$$HOME/.local/bin/$$script" ]; then \
			rm -f "$$HOME/.local/bin/$$script"; \
			echo "Removed $$HOME/.local/bin/$$script"; \
		fi; \
	done
	@echo "Clean completed"

uninstall:  ## Uninstall the package
	pip uninstall fzf-ai -y