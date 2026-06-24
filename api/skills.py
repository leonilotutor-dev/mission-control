"""API: skills listing."""
import os, yaml
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/home/hermes/.hermes"))


def get_skills():
    skills_dir = HERMES_HOME / "skills"
    if not skills_dir.is_dir():
        return {"skills": [], "total": 0, "categories": 0}

    result = []
    for child in sorted(skills_dir.iterdir()):
        skill_md = None
        name = child.name
        description = ""
        tags = []

        if child.is_dir():
            # Category dir — look for SKILL.md inside
            skill_file = child / "SKILL.md"
            if skill_file.exists():
                skill_md = skill_file
                name = child.name
        elif child.suffix == ".md":
            skill_md = child

        if skill_md:
            try:
                text = skill_md.read_text()
                # Parse YAML frontmatter between --- markers
                if text.startswith("---"):
                    parts = text.split("---", 2)
                    if len(parts) >= 3:
                        fm = yaml.safe_load(parts[1])
                        if fm and isinstance(fm, dict):
                            name = fm.get("name", name)
                            description = fm.get("description", "")
                            tags = fm.get("tags", fm.get("metadata", {}).get("hermes", {}).get("tags", []))
            except Exception:
                pass

        # Get category from parent
        category = child.parent.name if child.parent.name != "skills" else ""
        if child.is_dir():
            category = child.name

        result.append({
            "name": name,
            "category": category,
            "description": description[:120] if description else "",
            "tags": tags,
            "path": str(skill_md.relative_to(HERMES_HOME)) if skill_md else "",
        })

    categories = set(r["category"] for r in result if r["category"])

    return {"skills": result, "total": len(result), "categories": list(categories)}
