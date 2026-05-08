# Canvas API — What Lumina Can Access

> **Scope:** Everything below is accessible using the **student's own API key** only.
> Lumina never uses an admin token. Every call returns exactly what that student
> can see when they log into Canvas themselves. Nothing more.
>
> Base URL pattern: `https://{school}.instructure.com/api/v1/...`

---

## 1. User / Identity

| Endpoint | Key Fields Available |
|---|---|
| `GET /users/self` | `id`, `name`, `short_name`, `sortable_name`, `email`, `login_id`, `avatar_url`, `bio`, `time_zone`, `locale` |
| `GET /users/self/profile` | All above + `calendar.ics` (personal iCal URL), `primary_email`, `integration_id` |
| `GET /users/self/enrollments` | Course list with `enrollment_state` (active/completed/invited), `type` (StudentEnrollment/TeacherEnrollment), `grades` (if released) |

---

## 2. Courses

| Endpoint | Key Fields Available |
|---|---|
| `GET /courses?enrollment_state=active` | `id`, `name`, `course_code`, `account_id` (**sub-account — extracurricular signal**), `start_at`, `end_at`, `workflow_state`, `course_format` (online/blended/on_campus), `public_description`, `time_zone`, `default_view`, `syllabus_body` (HTML), `total_students`, `needs_grading_count` |
| `GET /courses/{id}` | All above + `term` (semester/year info), `permissions` (what student can do) |
| `GET /courses/{id}/settings` | `allow_student_discussion_topics`, `allow_student_forum_attachments`, `filter_speed_grader_by_student_group` |

### Fields useful for extracurricular classification
- `account_id` — most reliable: courses in a "Student Activities" sub-account will share the same `account_id`
- `course_format` — "online" vs "blended" vs "on_campus"
- `syllabus_body` — HTML description of the course; may explicitly say "extracurricular"
- Canvas calendar event frequency (see §8 below)

---

## 3. Modules & Pages (Course Content)

| Endpoint | Key Fields Available |
|---|---|
| `GET /courses/{id}/modules?include[]=items` | Module: `id`, `name`, `position`, `unlock_at`, `require_sequential_progress`, `state` (locked/unlocked/completed) |
| Module item fields | `id`, `title`, `type` (Assignment/Quiz/File/Page/ExternalUrl/Discussion/ExternalTool), `position`, `indent`, `completion_requirement`, `url`, `page_url`, `content_id` |
| `GET /courses/{id}/pages/{page_url}` | `title`, `body` (**full HTML content**), `published`, `updated_at`, `html_url`, `editing_roles`, `last_edited_by` |
| `GET /courses/{id}/pages` | Same as above but summary only (no body) |

### What this gives Lumina
Full text of every lecture note, reading, and resource page a teacher publishes — the primary knowledge base for the AI tutor.

---

## 4. Assignments

| Endpoint | Key Fields Available |
|---|---|
| `GET /courses/{id}/assignments?include[]=rubric` | See full list below |

### Assignment fields
| Field | Type | Notes |
|---|---|---|
| `id` | int | |
| `name` | string | Assignment title |
| `description` | HTML string | Full assignment brief — **strip to text for indexing** |
| `due_at` | ISO 8601 | Submission deadline |
| `lock_at` | ISO 8601 | After this time, submission is locked |
| `unlock_at` | ISO 8601 | Available from this time |
| `points_possible` | float | Max points |
| `submission_types` | array | `online_text_entry`, `online_upload`, `online_url`, `media_recording`, `none` (**sit-in exam**), `on_paper` (**paper exam**), `external_tool` |
| `allowed_extensions` | array | File types allowed (pdf, docx, etc.) |
| `grading_type` | string | `points`, `percent`, `letter_grade`, `gpa_scale`, `pass_fail`, `not_graded` |
| `html_url` | string | Canvas URL (not exposed to students in Lumina) |
| `rubric` | array | Grading criteria — see §4a |
| `rubric_settings` | object | `points_possible`, `free_form_criterion_comments` |
| `peer_reviews` | bool | Whether peer review is enabled |
| `group_category_id` | int | Non-null = group assignment |
| `position` | int | Order within module |
| `published` | bool | Hidden from students if false |

### 4a. Rubric structure
```json
[
  {
    "id": "abc123",
    "description": "Content Quality",
    "long_description": "Evaluates depth and accuracy of ideas",
    "points": 20,
    "criterion_use_range": false,
    "ratings": [
      { "id": "r1", "description": "Excellent", "long_description": "...", "points": 20 },
      { "id": "r2", "description": "Satisfactory", "long_description": "...", "points": 15 },
      { "id": "r3", "description": "Needs Work", "long_description": "...", "points": 10 },
      { "id": "r4", "description": "Insufficient", "long_description": "...", "points": 0 }
    ]
  }
]
```

### What Lumina cannot get from assignments
- Whether the student has submitted yet (needs submissions endpoint — see §6)
- Teacher's draft comments before they release feedback
- Other students' submissions

---

## 5. Quizzes / Assessments

| Endpoint | Key Fields Available |
|---|---|
| `GET /courses/{id}/quizzes` | See full list below |

### Quiz fields
| Field | Type | Notes |
|---|---|---|
| `id` | int | |
| `title` | string | |
| `description` | HTML | Instructions |
| `quiz_type` | string | `assignment` (graded), `practice_quiz`, `graded_survey`, `survey` |
| `due_at` | ISO 8601 | |
| `lock_at` / `unlock_at` | ISO 8601 | |
| `time_limit` | int (minutes) | **null = unlimited; non-null = timed exam** |
| `points_possible` | float | |
| `allowed_attempts` | int | -1 = unlimited |
| `shuffle_answers` | bool | |
| `show_correct_answers` | bool | Whether student can review after |
| `one_question_at_a_time` | bool | Exam-style sequencing |
| `cant_go_back` | bool | Locked navigation (common in formal exams) |
| `html_url` | string | |
| `mobile_url` | string | |
| `published` | bool | |

### Detecting formal exams from quizzes
`is_exam` heuristic (implemented in `canvas/client.py`):
- `time_limit` is set, **OR**
- Title contains: `exam`, `test`, `assessment`, `midterm`, `final`, `mock`, `summative`, `end of term`

---

## 6. Student Submissions (own only)

| Endpoint | Key Fields Available |
|---|---|
| `GET /courses/{id}/students/submissions?student_ids[]=self&include[]=submission_comments&include[]=rubric_assessment` | See below |
| `GET /courses/{id}/assignments/{id}/submissions/self` | Single assignment submission |

### Submission fields
| Field | Notes |
|---|---|
| `assignment_id` | Links to the assignment |
| `submitted_at` | When the student submitted |
| `submission_type` | How it was submitted (online_upload, online_text_entry, etc.) |
| `body` | Text entry content (**intentionally not indexed by Lumina — privacy**) |
| `attachments` | Metadata of uploaded files (name, size, content-type — NOT the file content) |
| `grade` | Teacher-assigned grade (only if released) |
| `score` | Numeric score (only if released) |
| `late` | bool |
| `missing` | bool — not submitted past due date |
| `excused` | bool |
| `workflow_state` | `submitted`, `graded`, `pending_review`, `unsubmitted` |
| `submission_comments` | Array of comment objects (teacher + student) |
| `rubric_assessment` | Per-criterion scores `{ criterion_id: { points, comments } }` |

### submission_comments fields
```json
{
  "id": 123,
  "author_id": 456,
  "author_name": "Mr. Smith",
  "comment": "Good analysis but cite your sources",
  "created_at": "2025-10-01T14:30:00Z",
  "attachments": [],
  "media_comment": null
}
```
> **Lumina indexes only comments where `author_id ≠ student user_id`** (teacher/TA feedback only).

### What Lumina cannot get
- Other students' submissions or grades
- Draft comments not yet released by teacher
- Submission file contents (only metadata)
- SpeedGrader annotations

---

## 7. Announcements

| Endpoint | Key Fields Available |
|---|---|
| `GET /v1/announcements?context_codes[]=course_{id}` | `title`, `message` (HTML body), `posted_at`, `author` (name, id), `read_state`, `discussion_subentry_count`, `attachments` |

---

## 8. Calendar Events (Meeting Frequency)

| Endpoint | Key Fields Available |
|---|---|
| `GET /calendar_events?context_codes[]=course_{id}&type=event` | `id`, `title`, `start_at`, `end_at`, `description` (HTML), `location_name`, `location_address`, `all_day`, `context_code` |
| `GET /calendar_events?context_codes[]=user_self&type=assignment` | All assignment due dates across ALL courses in one call |

### Extracurricular signal
Count events over 12 weeks per course:
- `weekly_meeting_frequency ≥ 2` → regular class schedule → likely **core subject**
- `weekly_meeting_frequency < 0.5` → sporadic/no meetings → likely **extra-curricular**

> ⚠️ For fully online schools (like Dwight Global) that run sessions via Zoom outside
> Canvas, this count may be 0 for core subjects. Use as a secondary hint only.

---

## 9. Files (Course Files)

| Endpoint | Key Fields Available |
|---|---|
| `GET /courses/{id}/files` | `id`, `display_name`, `filename`, `content-type`, `size`, `url` (download URL with auth token), `updated_at`, `lock_info`, `folder_id` |
| `GET /courses/{id}/folders` | Folder tree structure |

> **Note:** Lumina currently lists but does not download or index course files.
> A background indexer for teacher-uploaded PDFs is on the roadmap.

---

## 10. Grades

| Endpoint | Key Fields Available |
|---|---|
| `GET /courses/{id}/grades` | `current_grade`, `final_grade`, `current_score`, `final_score` (only if teacher has released grades) |
| `GET /users/self/enrollments` | Grades per course via `grades.current_grade` |

> **Lumina intentionally does not sync grades.** Reasons:
> 1. Grade visibility is controlled by the teacher — often hidden until term end
> 2. Showing grades out of context could cause student anxiety
> 3. Dwight uses a separate grading system (not Canvas gradebook as primary)
> The AI can discuss grade implications if a student shares them manually.

---

## 11. Discussions

| Endpoint | Key Fields Available |
|---|---|
| `GET /courses/{id}/discussion_topics` | `id`, `title`, `message` (HTML), `posted_at`, `assignment` (if graded), `discussion_type`, `require_initial_post` |
| `GET /courses/{id}/discussion_topics/{id}/entries` | Student-posted entries (visible if `require_initial_post` is met) |

---

## 12. Personal Calendar / iCal Feed

| Source | Details |
|---|---|
| **Canvas personal iCal URL** | Found at: `Canvas → Account → Settings → Calendar Feed` |
| **URL format** | `https://{school}.instructure.com/feeds/calendars/user_{canvas_id}.ics` |
| **iCal contents** | All assignment due dates + course calendar events + personal calendar events added by the student |
| **Suitable for** | Time-blocking: identifying when student is busy/free for study planning |
| **Also works with** | Google Calendar share URL (`.ics`), Apple iCal subscription link |

---

## 13. What Canvas API Does NOT Provide

| Item | Reason |
|---|---|
| Other students' data | API is scoped to the authenticated user only |
| Teacher-private content (unpublished pages/assignments) | `published: false` items are not returned |
| Internal teacher notes / SpeedGrader annotations | Teacher-only API scope |
| Zoom/Google Meet session recordings | External integrations, not Canvas-native |
| Email/inbox messages | Separate Canvas Conversations API (not currently synced) |
| Attendance records | School-specific LTI tools (not Canvas-native API) |
| Historical grade changes | Audit log is admin-only |
| Parents' view | Parent-portal data requires parent API token |
| School SIS data (timetable, homeroom) | Requires SIS integration or admin token |

---

## 14. Canvas API Scope Summary for Lumina

```
Student API Key Scope
━━━━━━━━━━━━━━━━━━━
✅ Currently synced         ⏳ Planned / Ready to build   ❌ Not applicable
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Course list + metadata    ⏳ Personal iCal / calendar   ❌ Other students
✅ Module pages (full text)  ⏳ Discussion threads         ❌ Teacher-private content
✅ Assignment descriptions   ⏳ Course files (PDF index)   ❌ Admin/SIS data
✅ Rubric criteria           ⏳ Grades (opt-in)            ❌ Parent portal
✅ Quiz/exam details         ⏳ Inbox/messages             ❌ Zoom recordings
✅ Announcements             ⏳ Syllabus indexing          ❌ Grade audit log
✅ Teacher feedback comments ⏳ Attendance (if LTI)
✅ Rubric assessment scores
✅ Meeting frequency signal
✅ Account_id (sub-account)
```
