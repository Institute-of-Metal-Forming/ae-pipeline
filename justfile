set default-list := true

# build the entire project using pytask optionally filtered by 'key'
build key="":
    uv run pytask build -k "{{ key }}"
