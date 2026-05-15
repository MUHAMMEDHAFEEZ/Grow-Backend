CREATE TABLE
    IF NOT EXISTS "django_migrations" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "app" varchar(255) NOT NULL,
        "name" varchar(255) NOT NULL,
        "applied" datetime NOT NULL
    );

CREATE TABLE
    sqlite_sequence (name, seq);

CREATE TABLE
    IF NOT EXISTS "django_content_type" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "app_label" varchar(100) NOT NULL,
        "model" varchar(100) NOT NULL
    );

CREATE UNIQUE INDEX "django_content_type_app_label_model_76bd3d3b_uniq" ON "django_content_type" ("app_label", "model");

CREATE TABLE
    IF NOT EXISTS "auth_group_permissions" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED,
        "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "auth_group_permissions_group_id_permission_id_0cd325b0_uniq" ON "auth_group_permissions" ("group_id", "permission_id");

CREATE INDEX "auth_group_permissions_group_id_b120cbf9" ON "auth_group_permissions" ("group_id");

CREATE INDEX "auth_group_permissions_permission_id_84c5c92e" ON "auth_group_permissions" ("permission_id");

CREATE TABLE
    IF NOT EXISTS "auth_permission" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "content_type_id" integer NOT NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
        "codename" varchar(100) NOT NULL,
        "name" varchar(255) NOT NULL
    );

CREATE UNIQUE INDEX "auth_permission_content_type_id_codename_01ab375a_uniq" ON "auth_permission" ("content_type_id", "codename");

CREATE INDEX "auth_permission_content_type_id_2f476e4b" ON "auth_permission" ("content_type_id");

CREATE TABLE
    IF NOT EXISTS "auth_group" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name" varchar(150) NOT NULL UNIQUE
    );

CREATE TABLE
    IF NOT EXISTS "accounts_user_groups" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "group_id" integer NOT NULL REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "accounts_user_user_permissions" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "permission_id" integer NOT NULL REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "accounts_user_groups_user_id_group_id_59c0b32f_uniq" ON "accounts_user_groups" ("user_id", "group_id");

CREATE INDEX "accounts_user_groups_user_id_52b62117" ON "accounts_user_groups" ("user_id");

CREATE INDEX "accounts_user_groups_group_id_bd11a704" ON "accounts_user_groups" ("group_id");

CREATE UNIQUE INDEX "accounts_user_user_permissions_user_id_permission_id_2ab516c2_uniq" ON "accounts_user_user_permissions" ("user_id", "permission_id");

CREATE INDEX "accounts_user_user_permissions_user_id_e4f0a161" ON "accounts_user_user_permissions" ("user_id");

CREATE INDEX "accounts_user_user_permissions_permission_id_113bb443" ON "accounts_user_user_permissions" ("permission_id");

CREATE TABLE
    IF NOT EXISTS "accounts_parentprofile" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "child_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "parent_id" bigint NOT NULL UNIQUE REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "accounts_parentprofile_parent_id_child_id_e32cc681_uniq" ON "accounts_parentprofile" ("parent_id", "child_id");

CREATE INDEX "accounts_parentprofile_child_id_cb9cef43" ON "accounts_parentprofile" ("child_id");

CREATE TABLE
    IF NOT EXISTS "accounts_passwordresettoken" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "token" char(32) NOT NULL UNIQUE,
        "created_at" datetime NOT NULL,
        "expires_at" datetime NOT NULL,
        "is_used" bool NOT NULL,
        "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "accounts_school" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name" varchar(255) NOT NULL,
        "slug" varchar(255) NOT NULL UNIQUE,
        "created_at" datetime NOT NULL,
        "created_by_id" bigint NOT NULL UNIQUE REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "accounts_passwordresettoken_user_id_2789bc5c" ON "accounts_passwordresettoken" ("user_id");

CREATE TABLE
    IF NOT EXISTS "accounts_enrollmentcode" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "token" char(32) NOT NULL UNIQUE,
        "status" varchar(10) NOT NULL,
        "used_at" datetime NULL,
        "revoked_at" datetime NULL,
        "created_at" datetime NOT NULL,
        "revoked_by_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "school_id" bigint NOT NULL REFERENCES "accounts_school" ("id") DEFERRABLE INITIALLY DEFERRED,
        "used_by_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "accounts_enrollmentcodeevent" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "event_type" varchar(20) NOT NULL,
        "created_at" datetime NOT NULL,
        "actor_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "code_id" bigint NOT NULL REFERENCES "accounts_enrollmentcode" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "accounts_enrollmentratelimit" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "failed_attempts" integer NOT NULL,
        "window_start" datetime NULL,
        "locked_until" datetime NULL,
        "user_id" bigint NOT NULL UNIQUE REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "accounts_schoolmembership" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "role" varchar(10) NOT NULL,
        "joined_at" datetime NOT NULL,
        "school_id" bigint NOT NULL REFERENCES "accounts_school" ("id") DEFERRABLE INITIALLY DEFERRED,
        "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "accounts_en_school__8ec846_idx" ON "accounts_enrollmentcode" ("school_id", "status");

CREATE INDEX "accounts_en_code_id_78d4a8_idx" ON "accounts_enrollmentcodeevent" ("code_id", "event_type");

CREATE INDEX "accounts_sc_user_id_da9eaa_idx" ON "accounts_schoolmembership" ("user_id", "role");

CREATE UNIQUE INDEX "accounts_schoolmembership_user_id_school_id_1ebf7714_uniq" ON "accounts_schoolmembership" ("user_id", "school_id");

CREATE INDEX "accounts_enrollmentcode_revoked_by_id_19ac3e34" ON "accounts_enrollmentcode" ("revoked_by_id");

CREATE INDEX "accounts_enrollmentcode_school_id_d064f8c4" ON "accounts_enrollmentcode" ("school_id");

CREATE INDEX "accounts_enrollmentcode_used_by_id_94ea3ed5" ON "accounts_enrollmentcode" ("used_by_id");

CREATE INDEX "accounts_enrollmentcodeevent_actor_id_ae7a9630" ON "accounts_enrollmentcodeevent" ("actor_id");

CREATE INDEX "accounts_enrollmentcodeevent_code_id_0f8d8242" ON "accounts_enrollmentcodeevent" ("code_id");

CREATE INDEX "accounts_schoolmembership_school_id_03b72f00" ON "accounts_schoolmembership" ("school_id");

CREATE INDEX "accounts_schoolmembership_user_id_700422b4" ON "accounts_schoolmembership" ("user_id");

CREATE TABLE
    IF NOT EXISTS "django_admin_log" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "object_id" text NULL,
        "object_repr" varchar(200) NOT NULL,
        "action_flag" smallint unsigned NOT NULL CHECK ("action_flag" >= 0),
        "change_message" text NOT NULL,
        "content_type_id" integer NULL REFERENCES "django_content_type" ("id") DEFERRABLE INITIALLY DEFERRED,
        "user_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "action_time" datetime NOT NULL
    );

CREATE INDEX "django_admin_log_content_type_id_c4bce8eb" ON "django_admin_log" ("content_type_id");

CREATE INDEX "django_admin_log_user_id_c564eba6" ON "django_admin_log" ("user_id");

CREATE TABLE
    IF NOT EXISTS "attendance_attendancerecord" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "date" date NOT NULL,
        "status" varchar(10) NOT NULL,
        "course_id" bigint NOT NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "marked_by_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "attendance_attendancerecord_course_id_student_id_date_6d959df4_uniq" ON "attendance_attendancerecord" ("course_id", "student_id", "date");

CREATE INDEX "attendance_attendancerecord_course_id_b94e0fcc" ON "attendance_attendancerecord" ("course_id");

CREATE INDEX "attendance_attendancerecord_marked_by_id_c49b69c9" ON "attendance_attendancerecord" ("marked_by_id");

CREATE INDEX "attendance_attendancerecord_student_id_d242c468" ON "attendance_attendancerecord" ("student_id");

CREATE INDEX "attendance__course__60d8cb_idx" ON "attendance_attendancerecord" ("course_id", "date");

CREATE INDEX "attendance__student_588cfe_idx" ON "attendance_attendancerecord" ("student_id", "date");

CREATE TABLE
    IF NOT EXISTS "grades_grade" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "score" decimal NOT NULL,
        "feedback" text NOT NULL,
        "graded_at" datetime NOT NULL,
        "graded_by_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "submission_id" bigint NOT NULL UNIQUE REFERENCES "submissions_submission" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "grades_grade_graded_by_id_3fdc91b9" ON "grades_grade" ("graded_by_id");

CREATE TABLE
    IF NOT EXISTS "schools_school" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name" varchar(255) NOT NULL,
        "school_code" varchar(50) NOT NULL UNIQUE,
        "school_type" varchar(20) NOT NULL,
        "address" text NULL,
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL
    );

CREATE TABLE
    IF NOT EXISTS "schools_grade" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name" varchar(100) NOT NULL,
        "level" integer NOT NULL,
        "stage" varchar(20) NOT NULL
    );

CREATE TABLE
    IF NOT EXISTS "schools_subject" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "name_ar" varchar(100) NOT NULL,
        "name_en" varchar(100) NOT NULL,
        "code" varchar(20) NOT NULL UNIQUE
    );

CREATE TABLE
    IF NOT EXISTS "schools_course" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "school_type" varchar(10) NOT NULL,
        "section" varchar(20) NULL,
        "is_active" bool NOT NULL,
        "grade_id" bigint NOT NULL REFERENCES "schools_grade" ("id") DEFERRABLE INITIALLY DEFERRED,
        "subject_id" bigint NOT NULL REFERENCES "schools_subject" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "schools_course_subject_id_grade_id_school_type_section_2ee599f5_uniq" ON "schools_course" (
    "subject_id",
    "grade_id",
    "school_type",
    "section"
);

CREATE INDEX "schools_course_grade_id_560299b6" ON "schools_course" ("grade_id");

CREATE INDEX "schools_course_subject_id_716de7a7" ON "schools_course" ("subject_id");

CREATE TABLE
    IF NOT EXISTS "django_session" (
        "session_key" varchar(40) NOT NULL PRIMARY KEY,
        "session_data" text NOT NULL,
        "expire_date" datetime NOT NULL
    );

CREATE INDEX "django_session_expire_date_a5c62663" ON "django_session" ("expire_date");

CREATE TABLE
    IF NOT EXISTS "students_student" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "full_name" varchar(150) NOT NULL,
        "school_code" varchar(50) NULL,
        "student_id" varchar(30) NOT NULL UNIQUE,
        "generated_password" varchar(30) NOT NULL,
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL,
        "grade_id" bigint NULL REFERENCES "schools_grade" ("id") DEFERRABLE INITIALLY DEFERRED,
        "school_id" bigint NULL REFERENCES "schools_school" ("id") DEFERRABLE INITIALLY DEFERRED,
        "user_id" bigint NULL UNIQUE REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "parent_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "parent_access_code" varchar(20) NULL
    );

CREATE INDEX "students_student_grade_id_37795273" ON "students_student" ("grade_id");

CREATE INDEX "students_student_school_id_be4a7ab9" ON "students_student" ("school_id");

CREATE INDEX "students_student_parent_id_c1069729" ON "students_student" ("parent_id");

CREATE TABLE
    IF NOT EXISTS "study_sessions_studysession" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "started_at" datetime NOT NULL,
        "ended_at" datetime NULL,
        "duration" integer NULL,
        "xp_earned" integer NOT NULL,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "study_sessions_studysession_student_id_c3cff4dd" ON "study_sessions_studysession" ("student_id");

CREATE INDEX "study_sessi_student_523997_idx" ON "study_sessions_studysession" ("student_id", "ended_at");

CREATE INDEX "study_sessi_student_5a6384_idx" ON "study_sessions_studysession" ("student_id", "started_at");

CREATE TABLE
    IF NOT EXISTS "token_blacklist_blacklistedtoken" (
        "blacklisted_at" datetime NOT NULL,
        "token_id" bigint NOT NULL UNIQUE REFERENCES "token_blacklist_outstandingtoken" ("id") DEFERRABLE INITIALLY DEFERRED,
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT
    );

CREATE TABLE
    IF NOT EXISTS "token_blacklist_outstandingtoken" (
        "token" text NOT NULL,
        "created_at" datetime NULL,
        "expires_at" datetime NOT NULL,
        "user_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "jti" varchar(255) NOT NULL UNIQUE,
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT
    );

CREATE INDEX "token_blacklist_outstandingtoken_user_id_83bc629a" ON "token_blacklist_outstandingtoken" ("user_id");

CREATE TABLE
    IF NOT EXISTS "dashboard_dashboardinsight" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "title" varchar(255) NOT NULL,
        "description" text NOT NULL,
        "severity" varchar(10) NOT NULL,
        "insight_type" varchar(30) NOT NULL,
        "recommendation" text NOT NULL,
        "is_dismissed" bool NOT NULL,
        "dismissed_at" datetime NULL,
        "related_object_type" varchar(50) NOT NULL,
        "related_object_id" integer NULL,
        "created_at" datetime NOT NULL,
        "dismissed_by_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "dashboard_interventionrecord" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "action" varchar(30) NOT NULL,
        "priority" integer NOT NULL,
        "status" varchar(15) NOT NULL,
        "notes" text NOT NULL,
        "created_at" datetime NOT NULL,
        "completed_at" datetime NULL,
        "assigned_to_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "dashboard_studentnote" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "note" text NOT NULL,
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL,
        "author_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "dashboard_dashboardinsight_dismissed_by_id_6275d44e" ON "dashboard_dashboardinsight" ("dismissed_by_id");

CREATE INDEX "dashboard_d_severit_4cd94b_idx" ON "dashboard_dashboardinsight" ("severity", "is_dismissed");

CREATE INDEX "dashboard_d_insight_2d682d_idx" ON "dashboard_dashboardinsight" ("insight_type", "created_at");

CREATE INDEX "dashboard_interventionrecord_assigned_to_id_b5d879c9" ON "dashboard_interventionrecord" ("assigned_to_id");

CREATE INDEX "dashboard_interventionrecord_student_id_af9afbfb" ON "dashboard_interventionrecord" ("student_id");

CREATE INDEX "dashboard_i_student_29a06b_idx" ON "dashboard_interventionrecord" ("student_id", "status");

CREATE INDEX "dashboard_studentnote_author_id_cb442e7c" ON "dashboard_studentnote" ("author_id");

CREATE INDEX "dashboard_studentnote_student_id_f82c4bed" ON "dashboard_studentnote" ("student_id");

CREATE INDEX "dashboard_s_student_252ba6_idx" ON "dashboard_studentnote" ("student_id", "created_at");

CREATE TABLE
    IF NOT EXISTS "courses_courseprogress" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "progress_percentage" decimal NOT NULL,
        "study_time_seconds" integer NOT NULL,
        "last_activity" datetime NULL,
        "completion_status" varchar(20) NOT NULL,
        "course_id" bigint NOT NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "courses_studentcourse" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "is_active" bool NOT NULL,
        "enrolled_at" datetime NOT NULL,
        "course_id" bigint NOT NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "courses_courseprogress_student_id_course_id_8a51e05d_uniq" ON "courses_courseprogress" ("student_id", "course_id");

CREATE INDEX "courses_courseprogress_course_id_6d7ba8c9" ON "courses_courseprogress" ("course_id");

CREATE INDEX "courses_courseprogress_student_id_40d41f04" ON "courses_courseprogress" ("student_id");

CREATE INDEX "courses_cou_course__b41f1e_idx" ON "courses_courseprogress" ("course_id", "completion_status");

CREATE UNIQUE INDEX "courses_studentcourse_course_id_student_id_285024f9_uniq" ON "courses_studentcourse" ("course_id", "student_id");

CREATE INDEX "courses_studentcourse_course_id_d0e4312a" ON "courses_studentcourse" ("course_id");

CREATE INDEX "courses_studentcourse_student_id_4bab3cc1" ON "courses_studentcourse" ("student_id");

CREATE INDEX "courses_stu_course__380df3_idx" ON "courses_studentcourse" ("course_id", "is_active");

CREATE TABLE
    IF NOT EXISTS "courses_lessonactivity" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "watch_duration_seconds" integer NOT NULL,
        "completed" bool NOT NULL,
        "last_opened_at" datetime NULL,
        "lesson_id" bigint NOT NULL REFERENCES "courses_lesson" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "courses_lessonactivity_student_id_lesson_id_b8f235be_uniq" ON "courses_lessonactivity" ("student_id", "lesson_id");

CREATE INDEX "courses_lessonactivity_lesson_id_9105edaf" ON "courses_lessonactivity" ("lesson_id");

CREATE INDEX "courses_lessonactivity_student_id_25a9a9f3" ON "courses_lessonactivity" ("student_id");

CREATE INDEX "courses_les_lesson__937d7f_idx" ON "courses_lessonactivity" ("lesson_id", "completed");

CREATE TABLE
    IF NOT EXISTS "courses_quizattempt" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "score" decimal NOT NULL,
        "attempt_number" integer NOT NULL,
        "submitted_at" datetime NOT NULL,
        "quiz_id" bigint NOT NULL REFERENCES "courses_quiz" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "courses_qui_student_ad5bb3_idx" ON "courses_quizattempt" ("student_id", "quiz_id", "attempt_number" DESC);

CREATE INDEX "courses_qui_quiz_id_ba6df3_idx" ON "courses_quizattempt" ("quiz_id");

CREATE UNIQUE INDEX "courses_quizattempt_student_id_quiz_id_attempt_number_4839f344_uniq" ON "courses_quizattempt" ("student_id", "quiz_id", "attempt_number");

CREATE INDEX "courses_quizattempt_quiz_id_b289d1d8" ON "courses_quizattempt" ("quiz_id");

CREATE INDEX "courses_quizattempt_student_id_e02f2d94" ON "courses_quizattempt" ("student_id");

CREATE TABLE
    IF NOT EXISTS "core_activitylog" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "event_type" varchar(50) NOT NULL,
        "target_id" integer unsigned NULL CHECK ("target_id" >= 0),
        "target_type" varchar(50) NULL,
        "metadata" text NULL CHECK (
            (
                JSON_VALID ("metadata")
                OR "metadata" IS NULL
            )
        ),
        "created_at" datetime NOT NULL,
        "actor_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "core_activitylog_actor_id_a06da199" ON "core_activitylog" ("actor_id");

CREATE INDEX "core_activi_event_t_60cf36_idx" ON "core_activitylog" ("event_type", "created_at");

CREATE INDEX "core_activi_actor_i_cbcc7a_idx" ON "core_activitylog" ("actor_id", "created_at");

CREATE TABLE
    IF NOT EXISTS "tasks_studenttask" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "content_type" varchar(50) NOT NULL,
        "content_id" integer unsigned NOT NULL CHECK ("content_id" >= 0),
        "title" varchar(255) NOT NULL,
        "status" varchar(20) NOT NULL,
        "created_at" datetime NOT NULL,
        "completed_at" datetime NULL,
        "course_id" bigint NOT NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT "uq_student_content" UNIQUE ("student_id", "content_type", "content_id")
    );

CREATE INDEX "tasks_studenttask_course_id_062f1d4a" ON "tasks_studenttask" ("course_id");

CREATE INDEX "tasks_studenttask_student_id_bdab669e" ON "tasks_studenttask" ("student_id");

CREATE INDEX "tasks_stude_student_b6b9f7_idx" ON "tasks_studenttask" ("student_id", "status");

CREATE INDEX "tasks_stude_course__9c0aad_idx" ON "tasks_studenttask" ("course_id", "status");

CREATE INDEX "tasks_stude_content_623473_idx" ON "tasks_studenttask" ("content_type", "content_id");

CREATE TABLE
    IF NOT EXISTS "accounts_user" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "password" varchar(128) NOT NULL,
        "last_login" datetime NULL,
        "is_superuser" bool NOT NULL,
        "username" varchar(150) NOT NULL UNIQUE,
        "first_name" varchar(150) NOT NULL,
        "last_name" varchar(150) NOT NULL,
        "is_staff" bool NOT NULL,
        "is_active" bool NOT NULL,
        "date_joined" datetime NOT NULL,
        "role" varchar(12) NOT NULL,
        "email" varchar(254) NOT NULL UNIQUE,
        "avatar" varchar(200) NOT NULL,
        "phone" varchar(20) NOT NULL,
        "school_id" bigint NULL REFERENCES "accounts_school" ("id") DEFERRABLE INITIALLY DEFERRED,
        "notifications_enabled" bool NOT NULL
    );

CREATE INDEX "accounts_user_school_id_815fb93b" ON "accounts_user" ("school_id");

CREATE TABLE
    IF NOT EXISTS "notifications_notification" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "title" varchar(255) NOT NULL,
        "body" text NOT NULL,
        "event_type" varchar(30) NOT NULL,
        "is_read" bool NOT NULL,
        "created_at" datetime NOT NULL,
        "recipient_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "related_content_id" integer unsigned NULL CHECK ("related_content_id" >= 0),
        "related_course_id" bigint NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "parent_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "reference_id" integer unsigned NULL CHECK ("reference_id" >= 0),
        "student_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT "unique_parent_notification" UNIQUE ("parent_id", "event_type", "reference_id")
    );

CREATE INDEX "notifications_notification_recipient_id_d055f3f0" ON "notifications_notification" ("recipient_id");

CREATE INDEX "notifications_notification_related_course_id_8f3b18da" ON "notifications_notification" ("related_course_id");

CREATE INDEX "notifications_notification_parent_id_db6d732c" ON "notifications_notification" ("parent_id");

CREATE INDEX "notifications_notification_student_id_3ac4d1a8" ON "notifications_notification" ("student_id");

CREATE INDEX "notificatio_recipie_4e3567_idx" ON "notifications_notification" ("recipient_id", "is_read");

CREATE INDEX "notificatio_related_9e7856_idx" ON "notifications_notification" ("related_course_id");

CREATE INDEX "notificatio_event_t_4562fd_idx" ON "notifications_notification" ("event_type", "created_at");

CREATE INDEX "notificatio_parent__752032_idx" ON "notifications_notification" ("parent_id", "is_read");

CREATE TABLE
    IF NOT EXISTS "study_sessions_loginhistory" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "login_date" date NOT NULL,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE UNIQUE INDEX "study_sessions_loginhistory_student_id_login_date_53dad696_uniq" ON "study_sessions_loginhistory" ("student_id", "login_date");

CREATE INDEX "study_sessions_loginhistory_student_id_b3085a4b" ON "study_sessions_loginhistory" ("student_id");

CREATE INDEX "study_sessi_student_1a73ec_idx" ON "study_sessions_loginhistory" ("student_id", "login_date" DESC);

CREATE TABLE
    IF NOT EXISTS "students_studentaddratelimit" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "failed_attempts" integer NOT NULL,
        "window_start" datetime NULL,
        "locked_until" datetime NULL,
        "user_id" bigint NOT NULL UNIQUE REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "xp_xptransaction" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "source" varchar(20) NOT NULL,
        "created_at" datetime NOT NULL,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "xp_amount" integer NOT NULL,
        "source_id" integer NULL,
        "source_type" varchar(20) NULL,
        CONSTRAINT "unique_xp_source" UNIQUE ("student_id", "source_type", "source_id")
    );

CREATE INDEX "xp_xptransaction_student_id_657c133e" ON "xp_xptransaction" ("student_id");

CREATE INDEX "xp_xptransa_student_12635c_idx" ON "xp_xptransaction" ("student_id", "created_at");

CREATE TABLE
    IF NOT EXISTS "students_otprecord" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "email" varchar(254) NOT NULL,
        "otp_code" varchar(128) NOT NULL,
        "created_at" datetime NOT NULL,
        "expires_at" datetime NOT NULL,
        "is_used" bool NOT NULL
    );

CREATE TABLE
    IF NOT EXISTS "students_dailymasterlog" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "date" date NOT NULL,
        "tasks_total" integer NOT NULL,
        "tasks_completed" integer NOT NULL,
        "level" integer NOT NULL,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT "unique_daily_master_log" UNIQUE ("student_id", "date")
    );

CREATE TABLE
    IF NOT EXISTS "students_lessoncompletion" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "completed_at" datetime NOT NULL,
        "lesson_id" bigint NOT NULL REFERENCES "courses_lesson" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT "unique_lesson_completion" UNIQUE ("student_id", "lesson_id")
    );

CREATE TABLE
    IF NOT EXISTS "students_loginhistory" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "login_date" date NOT NULL,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT "unique_daily_login" UNIQUE ("student_id", "login_date")
    );

CREATE TABLE
    IF NOT EXISTS "students_refreshtoken" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "token" varchar(128) NOT NULL UNIQUE,
        "created_at" datetime NOT NULL,
        "expires_at" datetime NOT NULL,
        "is_revoked" bool NOT NULL,
        "device_info" varchar(255) NOT NULL,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "students_studentcourseprogress" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "completed_lessons" integer NOT NULL,
        "total_lessons" integer NOT NULL,
        "completion_percentage" decimal NOT NULL,
        "course_id" bigint NOT NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT "unique_student_course_progress" UNIQUE ("student_id", "course_id")
    );

CREATE TABLE
    IF NOT EXISTS "students_studentnotification" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "type" varchar(30) NOT NULL,
        "reference_type" varchar(30) NOT NULL,
        "reference_id" integer NULL,
        "message" text NOT NULL,
        "is_read" bool NOT NULL,
        "created_at" datetime NOT NULL,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT "unique_student_notification" UNIQUE ("student_id", "type", "reference_id")
    );

CREATE TABLE
    IF NOT EXISTS "students_studentsession" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "login_time" datetime NOT NULL,
        "logout_time" datetime NULL,
        "duration" integer NULL,
        "is_active" bool NOT NULL,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "students_ot_email_7a209d_idx" ON "students_otprecord" ("email", "created_at");

CREATE INDEX "students_dailymasterlog_student_id_8afe14e9" ON "students_dailymasterlog" ("student_id");

CREATE INDEX "students_lessoncompletion_lesson_id_0d799153" ON "students_lessoncompletion" ("lesson_id");

CREATE INDEX "students_lessoncompletion_student_id_e4d70f5f" ON "students_lessoncompletion" ("student_id");

CREATE INDEX "students_loginhistory_student_id_5dd88af0" ON "students_loginhistory" ("student_id");

CREATE INDEX "students_lo_student_603bad_idx" ON "students_loginhistory" ("student_id", "login_date");

CREATE INDEX "students_refreshtoken_student_id_7b4c5699" ON "students_refreshtoken" ("student_id");

CREATE INDEX "students_re_student_096f0c_idx" ON "students_refreshtoken" ("student_id", "is_revoked");

CREATE INDEX "students_studentcourseprogress_course_id_0b26784e" ON "students_studentcourseprogress" ("course_id");

CREATE INDEX "students_studentcourseprogress_student_id_66ead055" ON "students_studentcourseprogress" ("student_id");

CREATE INDEX "students_studentnotification_student_id_b5585f69" ON "students_studentnotification" ("student_id");

CREATE INDEX "students_studentsession_student_id_80fc9eab" ON "students_studentsession" ("student_id");

CREATE INDEX "students_st_student_3c4034_idx" ON "students_studentsession" ("student_id", "is_active");

CREATE TABLE
    IF NOT EXISTS "assignments_assignment" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "title" varchar(255) NOT NULL,
        "description" text NOT NULL,
        "due_date" datetime NOT NULL,
        "created_at" datetime NOT NULL,
        "course_id" bigint NOT NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "created_by_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "late_penalty_xp" integer unsigned NOT NULL CHECK ("late_penalty_xp" >= 0),
        "max_score" decimal NOT NULL,
        "teacher_file" varchar(100) NOT NULL,
        "xp_reward" integer unsigned NOT NULL CHECK ("xp_reward" >= 0)
    );

CREATE INDEX "assignments_assignment_course_id_95e644ec" ON "assignments_assignment" ("course_id");

CREATE INDEX "assignments_assignment_created_by_id_400f0633" ON "assignments_assignment" ("created_by_id");

CREATE TABLE
    IF NOT EXISTS "courses_course" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "title" varchar(255) NOT NULL,
        "description" text NOT NULL,
        "created_at" datetime NOT NULL,
        "teacher_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "target_capacity" integer unsigned NOT NULL CHECK ("target_capacity" >= 0),
        "grade_id" bigint NULL REFERENCES "schools_grade" ("id") DEFERRABLE INITIALLY DEFERRED,
        "is_published" bool NOT NULL
    );

CREATE INDEX "courses_course_teacher_id_846fa526" ON "courses_course" ("teacher_id");

CREATE INDEX "courses_course_grade_id_91e3368a" ON "courses_course" ("grade_id");

CREATE TABLE
    IF NOT EXISTS "courses_lesson" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "title" varchar(255) NOT NULL,
        "content" text NOT NULL,
        "order" integer unsigned NOT NULL CHECK ("order" >= 0),
        "created_at" datetime NOT NULL,
        "course_id" bigint NOT NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "end_time" datetime NULL,
        "start_time" datetime NULL,
        "bonus_xp" integer unsigned NOT NULL CHECK ("bonus_xp" >= 0),
        "pdf_file" varchar(100) NOT NULL,
        "resources" varchar(100) NOT NULL,
        "status" varchar(10) NOT NULL,
        "video_url" varchar(200) NOT NULL,
        "xp_reward" integer unsigned NOT NULL CHECK ("xp_reward" >= 0)
    );

CREATE INDEX "courses_lesson_course_id_16bc4882" ON "courses_lesson" ("course_id");

CREATE TABLE
    IF NOT EXISTS "courses_quiz" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "title" varchar(255) NOT NULL,
        "max_score" decimal NOT NULL,
        "created_at" datetime NOT NULL,
        "course_id" bigint NOT NULL REFERENCES "courses_course" ("id") DEFERRABLE INITIALLY DEFERRED,
        "lesson_id" bigint NULL REFERENCES "courses_lesson" ("id") DEFERRABLE INITIALLY DEFERRED,
        "duration_minutes" integer unsigned NOT NULL CHECK ("duration_minutes" >= 0),
        "end_time" datetime NULL,
        "is_locked" bool NOT NULL,
        "start_time" datetime NULL,
        "teacher_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "xp_reward" integer unsigned NOT NULL CHECK ("xp_reward" >= 0)
    );

CREATE INDEX "courses_quiz_course_id_1a0543d1" ON "courses_quiz" ("course_id");

CREATE INDEX "courses_quiz_lesson_id_2bf49392" ON "courses_quiz" ("lesson_id");

CREATE INDEX "courses_quiz_teacher_id_38f0f1fb" ON "courses_quiz" ("teacher_id");

CREATE INDEX "courses_qui_course__ac0918_idx" ON "courses_quiz" ("course_id");

CREATE INDEX "courses_qui_lesson__ab07e2_idx" ON "courses_quiz" ("lesson_id");

CREATE INDEX "courses_qui_teacher_66b0f6_idx" ON "courses_quiz" ("teacher_id");

CREATE TABLE
    IF NOT EXISTS "courses_question" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "text" text NOT NULL,
        "order" integer unsigned NOT NULL CHECK ("order" >= 0),
        "quiz_id" bigint NOT NULL REFERENCES "courses_quiz" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "courses_question_quiz_id_7bd87b34" ON "courses_question" ("quiz_id");

CREATE TABLE
    IF NOT EXISTS "courses_answeroption" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "text" varchar(255) NOT NULL,
        "is_correct" bool NOT NULL,
        "question_id" bigint NOT NULL REFERENCES "courses_question" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "courses_answeroption_question_id_5ea5163d" ON "courses_answeroption" ("question_id");

CREATE TABLE
    IF NOT EXISTS "courses_quizsubmission" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "started_at" datetime NOT NULL,
        "submitted_at" datetime NULL,
        "raw_score" decimal NOT NULL,
        "max_score" decimal NOT NULL,
        "normalized_score" decimal NOT NULL,
        "xp_earned" integer NOT NULL,
        "status" varchar(20) NOT NULL,
        "quiz_id" bigint NOT NULL REFERENCES "courses_quiz" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "courses_quizsubmission_quiz_id_39fe17dc" ON "courses_quizsubmission" ("quiz_id");

CREATE INDEX "courses_quizsubmission_student_id_cafb99c8" ON "courses_quizsubmission" ("student_id");

CREATE INDEX "courses_qui_quiz_id_5a405f_idx" ON "courses_quizsubmission" ("quiz_id", "status");

CREATE UNIQUE INDEX "courses_quizsubmission_quiz_id_student_id_f34abe3a_uniq" ON "courses_quizsubmission" ("quiz_id", "student_id");

CREATE TABLE
    IF NOT EXISTS "submissions_submission" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "status" varchar(10) NOT NULL,
        "submitted_at" datetime NOT NULL,
        "assignment_id" bigint NOT NULL REFERENCES "assignments_assignment" ("id") DEFERRABLE INITIALLY DEFERRED,
        "student_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        "feedback" text NOT NULL,
        "file" varchar(100) NOT NULL,
        "is_graded" bool NOT NULL,
        "normalized_score" decimal NULL,
        "raw_score" decimal NULL,
        "xp_awarded" integer NULL,
        "content" text NOT NULL
    );

CREATE UNIQUE INDEX "submissions_submission_assignment_id_student_id_36c32b8e_uniq" ON "submissions_submission" ("assignment_id", "student_id");

CREATE INDEX "submissions_submission_assignment_id_2b14186a" ON "submissions_submission" ("assignment_id");

CREATE INDEX "submissions_submission_student_id_3d2cf37a" ON "submissions_submission" ("student_id");

CREATE TABLE
    IF NOT EXISTS "teachers_auditlog" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "actor_type" varchar(10) NOT NULL,
        "actor_id" integer unsigned NOT NULL CHECK ("actor_id" >= 0),
        "action" varchar(50) NOT NULL,
        "resource_type" varchar(50) NOT NULL,
        "resource_id" integer unsigned NULL CHECK ("resource_id" >= 0),
        "metadata" text NULL CHECK (
            (
                JSON_VALID ("metadata")
                OR "metadata" IS NULL
            )
        ),
        "ip_address" char(39) NULL,
        "created_at" datetime NOT NULL
    );

CREATE TABLE
    IF NOT EXISTS "teachers_otprecord" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "email" varchar(254) NOT NULL,
        "otp_hash" varchar(128) NOT NULL,
        "created_at" datetime NOT NULL,
        "expires_at" datetime NOT NULL,
        "is_used" bool NOT NULL
    );

CREATE TABLE
    IF NOT EXISTS "teachers_teachercode" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "code" varchar(50) NOT NULL UNIQUE,
        "is_used" bool NOT NULL,
        "created_at" datetime NOT NULL,
        "school_id" bigint NOT NULL REFERENCES "accounts_school" ("id") DEFERRABLE INITIALLY DEFERRED,
        "used_by_id" bigint NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "teachers_teachernotificationpreference" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "email_notifications" bool NOT NULL,
        "missing_assignments" bool NOT NULL,
        "new_submissions" bool NOT NULL,
        "teacher_id" bigint NOT NULL UNIQUE REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "teachers_teacherprofile" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "bio" text NOT NULL,
        "avatar" varchar(200) NOT NULL,
        "preferred_language" varchar(10) NOT NULL,
        "status" varchar(10) NOT NULL,
        "created_at" datetime NOT NULL,
        "updated_at" datetime NOT NULL,
        "school_id" bigint NOT NULL REFERENCES "accounts_school" ("id") DEFERRABLE INITIALLY DEFERRED,
        "teacher_code_id" bigint NULL REFERENCES "teachers_teachercode" ("id") DEFERRABLE INITIALLY DEFERRED,
        "user_id" bigint NOT NULL UNIQUE REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "teachers_devicesession" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "refresh_token_hash" varchar(128) NOT NULL,
        "device_info" varchar(255) NOT NULL,
        "ip_address" char(39) NULL,
        "last_active" datetime NOT NULL,
        "created_at" datetime NOT NULL,
        "teacher_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE TABLE
    IF NOT EXISTS "teachers_refreshtoken" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "token_hash" varchar(128) NOT NULL,
        "expires_at" datetime NOT NULL,
        "is_revoked" bool NOT NULL,
        "device_info" varchar(255) NOT NULL,
        "ip_address" char(39) NULL,
        "created_at" datetime NOT NULL,
        "teacher_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED
    );

CREATE INDEX "teachers_te_code_3ca341_idx" ON "teachers_teachercode" ("code", "school_id");

CREATE TABLE
    IF NOT EXISTS "teachers_teachernotification" (
        "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
        "event_type" varchar(30) NOT NULL,
        "reference_type" varchar(50) NOT NULL,
        "reference_id" integer unsigned NULL CHECK ("reference_id" >= 0),
        "message" text NOT NULL,
        "is_read" bool NOT NULL,
        "created_at" datetime NOT NULL,
        "teacher_id" bigint NOT NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED,
        CONSTRAINT "unique_teacher_notification" UNIQUE ("teacher_id", "event_type", "reference_id")
    );

CREATE INDEX "teachers_au_actor_t_5a3c1f_idx" ON "teachers_auditlog" ("actor_type", "actor_id");

CREATE INDEX "teachers_au_resourc_107dc8_idx" ON "teachers_auditlog" ("resource_type", "resource_id");

CREATE INDEX "teachers_au_action_ae4429_idx" ON "teachers_auditlog" ("action", "created_at");

CREATE INDEX "teachers_ot_email_a90be9_idx" ON "teachers_otprecord" ("email", "created_at");

CREATE INDEX "teachers_teachercode_school_id_75afa6c8" ON "teachers_teachercode" ("school_id");

CREATE INDEX "teachers_teachercode_used_by_id_7b1d55f6" ON "teachers_teachercode" ("used_by_id");

CREATE INDEX "teachers_teacherprofile_school_id_20904357" ON "teachers_teacherprofile" ("school_id");

CREATE INDEX "teachers_teacherprofile_teacher_code_id_c969688f" ON "teachers_teacherprofile" ("teacher_code_id");

CREATE INDEX "teachers_devicesession_teacher_id_910ef99b" ON "teachers_devicesession" ("teacher_id");

CREATE INDEX "teachers_de_teacher_4a25be_idx" ON "teachers_devicesession" ("teacher_id", "last_active");

CREATE INDEX "teachers_refreshtoken_token_hash_acf960fe" ON "teachers_refreshtoken" ("token_hash");

CREATE INDEX "teachers_refreshtoken_teacher_id_db4a1d3c" ON "teachers_refreshtoken" ("teacher_id");

CREATE INDEX "teachers_re_teacher_e93479_idx" ON "teachers_refreshtoken" ("teacher_id", "is_revoked");

CREATE INDEX "teachers_teachernotification_teacher_id_a7d30e19" ON "teachers_teachernotification" ("teacher_id");

CREATE INDEX "teachers_te_teacher_b38f84_idx" ON "teachers_teachernotification" ("teacher_id", "is_read");

CREATE INDEX "teachers_te_teacher_66ef86_idx" ON "teachers_teachernotification" ("teacher_id", "event_type", "reference_id");

CREATE INDEX "teachers_te_school__1bba1d_idx" ON "teachers_teacherprofile" ("school_id", "status");