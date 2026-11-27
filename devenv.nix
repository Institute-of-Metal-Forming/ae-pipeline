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
    venv.enable = true;
    lsp.package = pkgs.ty;
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  treefmt = {
    enable = true;
    config.settings = {
      excludes = [
        ".*/*"
        "_*/*"
        "**/.*/*"
        "**/_*/*"
        ".gitignore"
        "**/.gitignore"
      ];
    };
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
      yamlfmt = {
        enable = true;
        settings = {
          formatter = {
            indent = 4;
          };
        };
      };
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
    sqlitebrowser
    # shared library needed by the numpy wheel (libz.so.1)
    zlib
    # TeX toolchain for matplotlib text.usetex with siunitx (spec 0010 R6)
    (texliveSmall.withPackages (
      ps: with ps; [
        siunitx
        type1cm
        cm-super
        dvipng
        underscore
      ]
    ))
  ];
}
