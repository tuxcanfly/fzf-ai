# typed: false
# frozen_string_literal: true

class FzfAi < Formula
  desc "Fuzzy-find and resume any AI coding session"
  homepage "https://github.com/tuxcanfly/fzf-ai"
  url "https://github.com/tuxcanfly/fzf-ai/archive/refs/tags/v2.0.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"

  depends_on "python@3.13"
  depends_on "fzf"

  def install
    # Install Python dependencies
    system "python3", "-m", "pip", "install", "--prefix=#{prefix}",
           "orjson", "pygments"

    # Install scripts
    bin.install "bin/fzf-ai"
    bin.install "bin/fzf-ai-index"
    bin.install "bin/fzf-ai-preview"
    bin.install "bin/fzf-ai-resume"
    bin.install "bin/fzf-ai-ui"
    bin.install "bin/fzf-ai-actions"
    bin.install "bin/fzf-ai-highlight"
    bin.install "bin/fzf-ai-stats"
    bin.install "bin/version.py"

    # Install plugin system
    (libexec/"stores").install "bin/stores/__init__.py"
    (libexec/"stores").install "bin/stores/EXAMPLE.py"
  end

  test do
    system "#{bin}/fzf-ai-index", "--help"
  end
end
