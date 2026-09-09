set default-list

# build the entire project using pytask optionally filtered by 'key'
build key="":
    uv run pytask build -k "{{ key }}"
