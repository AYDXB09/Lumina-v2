<!-- Canonical copy. The in-app page at /privacy renders frontend/src/legal/privacy.md, which must stay identical to this file. -->
# Privacy Policy

**Last updated: October 9, 2026**

This policy explains what information Lumina collects, where it goes, and how you can delete it. Lumina is a small, independently built project, so this describes what the app actually does, in the order a student would meet it, not generic boilerplate.

> **Pilot notice.** Lumina is a pilot, not yet rolled out school-wide. A data-processing agreement with a school has not been signed yet, and there is no parent-consent workflow yet. Until both exist, Lumina asks that users be at least 13 and that anyone under 18 has a parent or guardian's permission and their school's okay (see [Section 7](#7-students-and-age)).

## 1. What Lumina is

Lumina is an AI study companion for students who use Canvas. You connect your Canvas account once; Lumina reads your courses and assignments, and an AI tutor answers questions with that context. Lumina is built and operated by Anvith Yalamanchili, a student, and is not an official product of any school.

## 2. Information we collect

| What | Where it comes from | Why |
|---|---|---|
| **Email and password** | You, at sign-up | To sign you in. The password is handled entirely by our authentication provider (Supabase Auth); Lumina never sees or stores it in plain text. |
| **Canvas profile** — name, Canvas user ID, login/email, profile picture link, whether you're a student or teacher | Canvas, read with your access token | To show who you are and decide which features you see. |
| **Canvas access token** | You, at sign-up | To read your Canvas data. It is **encrypted at rest**; only its last 4 characters are ever shown back to you. Lumina only ever *reads* from Canvas. It never submits work, posts, or changes anything. |
| **Courses and course content** — course names and codes, module pages, assignment descriptions, rubrics and due dates, quiz/exam details, announcements | Canvas | So the tutor knows what you're studying. This is course material, so one copy is shared by everyone enrolled in the same course, not a private copy per student. |
| **Calendar links and events** — the Canvas calendar link, any personal calendar (.ics) links you add, and the events fetched from them (title, time, location, description) | Canvas and you | So the tutor and study plan can see what time is already taken. |
| **Chat history** — your messages, the AI's replies, a conversation title (the start of your first message), response time | You | To restore your conversations. A text file you attach in chat is pasted into your message and **saved with it**. Images you attach are sent to the AI for that request but **not saved**. |
| **Study materials you upload** — extracted text of PDFs and text files, filename, size, auto-detected subject/grade tags | You | So the tutor can search your own notes. **The original file is not kept**, only its extracted text, split into passages. |
| **Learning data** — practice-quiz questions and answers, scores, per-topic mastery levels, mind maps, your study plan | Generated as you use Lumina | To adapt quiz difficulty and keep your plan between visits. |
| **Session records** — a hashed sign-in token, sign-in method, created/last-used/expiry times | Created at sign-in | To keep you signed in for up to 90 days. No device or IP address is stored in this record. |
| **Last-active time** | Created as you use Lumina | Basic account upkeep. |

**Not collected:** we don't use analytics, advertising trackers or tracking cookies. The only cookie is a sign-in cookie (`lumina_refresh`: httpOnly, Secure, only sent to Lumina's sign-in endpoints). Your display preferences (theme, font size) are kept in your browser's local storage and never sent to us. Your short-lived access token is held in memory only.

**Server logs.** The hosting provider keeps operational logs (requests and errors). Lumina is set up so these don't contain passwords, Canvas tokens, calendar links or API keys, and we don't intentionally log the content of your conversations. They can contain internal account and course IDs. Our infrastructure providers may also keep their own network-level logs (such as IP addresses) under their own policies.

**Grades and feedback.** Your grades and your teachers' comments on your own work are fetched from Canvas **live, only for you, when you open the Feedback tab**. They are not stored in Lumina's database and not shown to other students.

## 3. What is sent to the AI provider

Lumina uses a third-party AI service to write answers, quiz questions and study plans, and to turn text into numbers for search. **The provider is whichever one Lumina is configured with; right now that is Google's Gemini API.** When you use the AI features, this is what leaves Lumina:

| Feature | Sent to the AI provider |
|---|---|
| **Chat** | Your recent messages (up to the last 4), including any text or images you attached, plus context Lumina adds: today's date, the names of your enrolled courses, the selected course's assignment and quiz titles and due dates, your calendar events for the next 15 days (title, time, location, from Canvas and any personal calendars you connected), and up to 3 passages found in your course content and your uploaded notes. |
| **Practice quiz** | The topic, difficulty level, and passages from your course content and notes. |
| **Study plan** | Course names, assignment/quiz/exam titles and due dates (not your calendar). |
| **Search (embeddings)** | Course text when it is indexed, text from notes you upload, and each question you type, sent to turn text into search vectors. |
| **Mind map** | Nothing. It is built from course content inside Lumina, with no AI call. |

**Never sent to the AI by Lumina:** your name, email, password, Canvas token, or grades and teacher comments. (Anything you type or attach yourself is sent, so don't include these.)

**Current provider terms, in plain words.** Lumina currently uses Google's Gemini API on its **unpaid (free) tier**. Google's published terms for that tier say Google may use submitted content and the responses to improve its products, that human reviewers may read it, and that personal or sensitive information should not be submitted. They also set age limits for apps built on the API. Google's paid tier is treated differently: it does not use prompts and responses to improve its products. This is a limitation of the pilot, and it is a reason to **not paste anything into Lumina that you wouldn't want a third party to see**, such as other people's personal details, passwords, or health information. If the provider or its terms change, this section will be updated.

## 4. Other services that handle your data

| Service | Role | What it sees |
|---|---|---|
| **Supabase** | Database and sign-in (hosted in the US) | Everything stored under Section 2, plus your email and password hash |
| **Railway** | Hosts the Lumina app and its server logs | Requests passing through the app, including your messages in transit |
| **Google** | AI provider (Section 3) | What is listed in Section 3 |
| **Canvas / your school** | The source of your course data | Lumina's read-only requests, made with your token |
| **Email relay** (via Supabase Auth) | Delivers password-reset emails | Your email address and the reset link, only when you request a reset |
| **Google Fonts and jsDelivr** | Load fonts and math-rendering styles in your browser | Your IP address and browser details, as with any website |
| **Interactive diagrams** (Desmos, PhET, EconGraphs, KineticGraphs, EPAM, Explorable Explanations) | Shown inside a chat reply when the tutor includes a diagram or simulation | Your IP address and browser details, loaded from their sites. **No Lumina account data is sent to them.** |

We do not sell or rent your information, and we don't use it for advertising.

## 5. Who can see your data

Other students cannot see your chats, notes, quizzes, plans, calendars or feedback. The database has row-level security turned on for every table with no browser access, so only Lumina's server can read it. Teacher accounts can upload documents to a school-wide knowledge base that students' tutors can search. They have no view of student activity. The person who runs Lumina can technically access the database in order to maintain it, and does not browse conversations except to investigate a problem you report or a security issue.

## 6. How long we keep it, and deleting your account

Your data is kept while your account exists. You can remove things piece by piece (the **New chat** button deletes a conversation, you can delete an uploaded file, and you can remove a calendar), or **delete your whole account at any time in Settings → Account → Danger zone**. You'll need to type `DELETE` and re-enter your password. It happens immediately and **cannot be undone**.

**Deleting your account removes:** your profile and encrypted Canvas token, all chats and messages, uploaded study materials, quiz attempts and mastery scores, mind maps, study plan, calendar links and cached events, sign-in records, and your sign-in identity (email and password hash), all in a single step.

**It does not remove:**
- Course material copied from Canvas (pages, assignments, announcements). It is shared by everyone in the course and isn't yours.
- Documents a teacher uploaded to the school-wide knowledge base. They stay with the school, and the link to the uploader is removed.
- Anonymous system records with no personal data (for example, a log of configuration changes).
- Anything already sent to the AI provider, which is governed by that provider's retention, and server or backup copies held by our infrastructure providers for a limited time.
- Your data in Canvas itself, which Lumina can't change. To cut Lumina off from Canvas immediately, delete the access token you created in Canvas → Account → Settings.

Expired sign-in records are not yet cleaned up automatically; yours are removed with your account.

## 7. Students and age

Lumina is meant for students and teachers at schools that use Canvas. You must be **at least 13** to create an account. If you're under 18, you should have a parent or guardian's permission and follow your school's rules. This is an honor-system requirement: Lumina does not currently verify age, and a parental-consent workflow is planned but not built. Lumina does not knowingly collect information from children under 13; if we learn an account belongs to a child under 13 it will be deleted.

## 8. Security

- Canvas tokens are encrypted before they are stored, and passwords are never stored by Lumina.
- Everything travels over HTTPS; the sign-in cookie is httpOnly and Secure.
- Calendar links are stored as plain links (they're needed to fetch your calendar), so treat them like passwords and don't share them.
- Lumina has not had a formal third-party security audit, and it runs on small-scale hosting. No system is perfectly secure.

## 9. Your choices

- Change or remove your Canvas key, calendars and uploaded notes any time in **Settings**.
- Delete a conversation (New chat) or your entire account (Settings → Account → Danger zone).
- There's no self-service data export yet.

## 10. Changes to this policy

If this policy changes in a meaningful way, we'll update the "Last updated" date above.

## 11. Questions

Ask your teacher or school administrator, who can pass your question to the person who runs Lumina. Deleting your account doesn't require anyone's help. It's all in Settings.
