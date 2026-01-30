# Sample Mermaid Files

This directory contains example Mermaid diagram files for testing the mermaid2gif converter.

## Files

### 1. sample.mmd
Basic top-down flowchart with decision logic.
```bash
uv run python -m src.main -i sample-mermaid-files/flowchart-td.mmd
```

### 2. flowchart-lr.mmd
Horizontal (left-to-right) flowchart demonstrating wide diagram support.
```bash
uv run python -m src.main -i sample-mermaid-files/flowchart-lr.mmd
```

### 3. sequence.mmd
Sequence diagram showing user-system-database interaction.
```bash
uv run python -m src.main -i sample-mermaid-files/sequence.mmd
```

### 4. er-diagram.mmd
Entity-Relationship diagram with teacher-student-department relationships.
```bash
uv run python -m src.main -i sample-mermaid-files/er-diagram.mmd
```

### 5. mermaid2gif.mmd
This project flow diagram
```bash
uv run python -m src.main -i sample-mermaid-files/mermaid2gif.mmd
```

## Usage

All samples can be converted with:
```bash
# Basic usage
uv run python -m src.main -i sample-mermaid-files/<filename>.mmd

# With verbose output
uv run python -m src.main -i sample-mermaid-files/<filename>.mmd -v

# With custom output path
uv run python -m src.main -i sample-mermaid-files/<filename>.mmd -o custom-output.gif
```

## Expected Results

- **Output:** GIFs saved to `output/` directory
- **Quality:** Sharp, high-resolution output
- **Animation:** Flowing arrow animations
- **Loop:** Seamless infinite loop
