# Mermaid Diagrams JSON Files

This directory contains JSON files with Mermaid diagram definitions for the referral workflow state machine. These files are designed for frontend integration.

## File Structure

Each JSON file follows this structure:

```json
{
  "diagram": "stateDiagram-v2\n    [*] --> referral_received\n    ..."
}
```

The `diagram` field contains the Mermaid script as a string with escaped newlines (`\n`).

## Available Files

1. **sample_diagram.json** - Base diagram showing the complete workflow structure
2. **scenario_1_referral_received.json** - Diagram when current state is `referral_received`
3. **scenario_2_completed.json** - Diagram when current state is `completed`
4. **scenario_3_needs_review.json** - Diagram when current state is `needs_review`
5. **scenario_4_incomplete.json** - Diagram when current state is `incomplete`
6. **scenario_5_rejected.json** - Diagram when current state is `rejected`

## Usage Example

```javascript
// Load the JSON file
const diagramData = require('./scenario_1_referral_received.json');

// Use with Mermaid.js
import mermaid from 'mermaid';
mermaid.initialize({ startOnLoad: true });
mermaid.render('diagram-id', diagramData.diagram);
```

## Color Coding

- **Green** (`#e6ffed`): Completed states (states that have been passed through)
- **Yellow** (`#fffbdd`): Current state (except rejected)
- **Red** (`#ffe6e6`): Rejected state (current state when rejected)

## State Transitions

The workflow supports the following transitions:
- `referral_received` → `completed`, `needs_review`, `incomplete`, or `rejected`
- `needs_review` → `referral_received` (can return)
- `incomplete` → `referral_received` (can return)
