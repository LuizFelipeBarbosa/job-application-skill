CREATE TABLE `applications` (
	`id` text PRIMARY KEY NOT NULL,
	`run_id` text NOT NULL,
	`run_status` text DEFAULT '' NOT NULL,
	`run_target` integer DEFAULT 0 NOT NULL,
	`run_created_at` text DEFAULT '' NOT NULL,
	`run_completed_at` text DEFAULT '' NOT NULL,
	`company` text NOT NULL,
	`title` text NOT NULL,
	`job_type` text DEFAULT 'Full-time / unspecified' NOT NULL,
	`job_id` text DEFAULT '' NOT NULL,
	`location` text NOT NULL,
	`site` text NOT NULL,
	`url` text DEFAULT '' NOT NULL,
	`canonical_url` text DEFAULT '' NOT NULL,
	`automation_status` text NOT NULL,
	`reason_code` text DEFAULT '' NOT NULL,
	`status_history_json` text DEFAULT '[]' NOT NULL,
	`created_at` text DEFAULT '' NOT NULL,
	`recorded_at` text DEFAULT '' NOT NULL,
	`updated_at` text DEFAULT '' NOT NULL,
	`submitted_at` text DEFAULT '' NOT NULL,
	`generated_answer_count` integer DEFAULT 0 NOT NULL,
	`inferred_answer_count` integer DEFAULT 0 NOT NULL,
	`career_stage` text DEFAULT '' NOT NULL,
	`career_stage_updated_at` text DEFAULT '' NOT NULL,
	`next_action_due_at` text DEFAULT '' NOT NULL,
	`stage_history_json` text DEFAULT '[]' NOT NULL,
	`import_id` text NOT NULL,
	`imported_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `applications_status_idx` ON `applications` (`automation_status`);--> statement-breakpoint
CREATE INDEX `applications_job_type_idx` ON `applications` (`job_type`);--> statement-breakpoint
CREATE INDEX `applications_recorded_at_idx` ON `applications` (`recorded_at`);