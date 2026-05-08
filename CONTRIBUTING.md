# Contributing — MetaScope API

Cảm ơn bạn đã muốn contribute! Đọc hướng dẫn bên dưới trước khi bắt đầu.

> **AI Agents**: đọc thêm `AGENTS.md` để biết đầy đủ code conventions và patterns.

---

## Quy trình làm việc

```
1. Đọc AGENTS.md (bắt buộc)
2. Setup hooks (chạy 1 lần):  make setup-hooks
3. Tạo branch từ main:       git checkout -b feat/your-feature main
4. Code + test
5. Commit (hooks tự chạy lint + format + validate commit message)
6. Push:                      git push -u origin feat/your-feature
7. Tạo PR trên GitHub
```

---

## Branch Naming

Format: `<type>/<short-description>`

| Type | Dùng khi | Ví dụ |
|---|---|---|
| `feat` | Thêm tính năng mới | `feat/riot-client` |
| `fix` | Sửa bug | `fix/rate-limit-429` |
| `refactor` | Refactor không đổi behavior | `refactor/service-layer` |
| `docs` | Chỉ thay đổi docs | `docs/api-reference` |
| `test` | Chỉ thêm/sửa test | `test/collector-coverage` |
| `chore` | Config, CI, deps, tooling | `chore/docker-compose` |

Quy tắc:
- **kebab-case** (chữ thường, dấu gạch ngang)
- Ngắn gọn, tối đa 3–4 từ sau type
- Có thể thêm phase prefix: `feat/phase1-riot-client`
- Không dùng tên người, ngày tháng, hay ticket ID

---

## Commit Messages

Format: [Conventional Commits](https://www.conventionalcommits.org/)

```
<type>(<scope>): <subject>

<body>           ← optional, giải thích WHY
<footer>         ← optional, breaking changes
```

### Type (bắt buộc)

`feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

### Scope (optional)

Module chính bị ảnh hưởng: `collector`, `api`, `models`, `services`, `core`, `docker`

### Subject (bắt buộc)

- Tiếng Anh
- Không viết hoa chữ đầu
- Không dấu chấm cuối
- Imperative mood: "add", "fix", "update" — không "added", "fixes"
- Tối đa 72 ký tự

### Ví dụ

```bash
# ✅ Đúng
feat(collector): add riot client with token bucket rate limiter
fix(api): return 404 instead of 500 when player not found
refactor(services): extract tier score calculation to pure function
test(collector): add unit tests for transformer edge cases
docs(api): add tier-list endpoint to API.md
chore(docker): upgrade python base image to 3.13

# ❌ Sai
Added riot client                      # thiếu type, past tense
feat: update stuff                     # quá mơ hồ
fix(api): Fixed the bug.               # past tense, dấu chấm
FEAT(collector): Add Riot Client       # viết hoa
```

### Body

Chỉ viết khi subject chưa đủ rõ. Giải thích **tại sao**, không mô tả **cái gì**.

---

## Pull Requests

- PR title theo format commit: `feat(collector): add riot client rate limiter`
- Mô tả ngắn gọn what & why trong PR description
- Mọi PR phải pass `make check && make test` trước khi merge
- Không merge nếu có conflict — rebase trước

---

## Checklist trước khi tạo PR

- [ ] Branch tạo từ `main` mới nhất
- [ ] Tất cả tests pass: `make test`
- [ ] Lint + typecheck pass: `make check`
- [ ] Commit messages đúng format Conventional Commits
- [ ] Không commit `.env`, `__pycache__/`, `htmlcov/`, hay file generated
- [ ] Cập nhật `docs/API.md` nếu thêm/sửa endpoint

---

## Những điều KHÔNG làm

- Không commit trực tiếp vào `main`
- Không force push lên branch đang có người review
- Không commit file nhạy cảm (`.env`, credentials, API keys)
- Không commit file generated (`htmlcov/`, `__pycache__/`, `.mypy_cache/`)
- Không viết commit message kiểu `wip`, `fix fix fix`, `asdfgh`

---

## Môi trường Dev

Toàn bộ chạy qua Docker — xem README.md để setup. Mọi command qua `make`:

```bash
make dev          # Start full stack
make test         # Run tests (inside Docker)
make check        # Lint + typecheck (inside Docker)
make migrate      # Run DB migrations (inside Docker)
```

Không chạy `pytest`, `ruff`, `alembic` trực tiếp trên host.

---

## Pre-commit Hooks

Hooks tự động chạy mỗi khi `git commit`. Setup 1 lần:

```bash
make setup-hooks
```

### Hooks chạy khi commit (pre-commit stage)

| Hook | Mô tả |
|---|---|
| `trailing-whitespace` | Xóa whitespace thừa cuối dòng |
| `end-of-file-fixer` | Đảm bảo newline cuối file |
| `check-yaml` / `check-toml` | Validate syntax YAML/TOML |
| `check-added-large-files` | Block file > 500KB |
| `check-merge-conflict` | Block nếu còn conflict markers |
| `detect-private-key` | Block nếu commit private key |
| `no-commit-to-branch` | **Block commit trực tiếp vào `main`** |
| `ruff` | Lint + auto-fix |
| `ruff-format` | Auto-format code |
| `mypy` | Type checking |

### Hooks chạy khi viết commit message (commit-msg stage)

| Hook | Mô tả |
|---|---|
| `conventional-pre-commit` | **Validate commit message** đúng Conventional Commits format |

Nếu hook fail → commit bị reject → fix lỗi → commit lại.

---

## Merge Rules

### Branch protection cho `main`

| Rule | Chi tiết |
|---|---|
| **Không push trực tiếp** | Mọi thay đổi qua PR |
| **Require PR review** | Ít nhất 1 approval (nếu có collaborator) |
| **Require status checks** | `make check` + `make test` phải pass |
| **No force push** | Lịch sử `main` không được rewrite |
| **Delete branch after merge** | Auto-delete branch sau khi merge |
| **Linear history** | Squash merge hoặc rebase, không merge commit |

### Merge strategy

Dùng **squash merge** cho tất cả PRs:
- Gom tất cả commits thành 1 commit trên `main`
- Commit message = PR title (đã theo Conventional Commits format)
- Lịch sử `main` clean và dễ đọc

```bash
# GitHub sẽ tự squash khi merge PR
# Hoặc manual:
git checkout main
git merge --squash feat/your-feature
git commit -m "feat(collector): add riot client with rate limiter"
```
