{
  pkgs,
  ...
}:
{
  enterShell = ''
    python --version
  '';

  languages.nix.enable = true;

  languages.python = {
    enable = true;
    version = "3.14";
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  treefmt = {
    enable = true;
    config.programs = {
      nixfmt.enable = true;
      ruff.enable = true;
      ruff-format.includes = [
        "*.py"
        "*.pyi"
        "*.ipynb"
      ];
      just.enable = true;
      taplo.enable = true;
      mdformat = {
        enable = true;
        plugins =
          ps: with ps; [
            mdformat-gfm
            mdformat-frontmatter
          ];
        settings = {
          wrap = "keep";
          number = true;
        };
      };
    };
  };

  git-hooks.hooks = {
    treefmt.enable = true;
  };

  packages = with pkgs; [
    nil
    just
    codebook
    nail-parquet
  ];
}
