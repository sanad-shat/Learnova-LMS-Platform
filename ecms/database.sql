BEGIN TRANSACTION;
CREATE TABLE activity (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	score FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(course_id) REFERENCES course (id)
);
CREATE TABLE assignment (
	id INTEGER NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	description TEXT, 
	assignment_type VARCHAR(50) NOT NULL, 
	start_date DATETIME NOT NULL, 
	due_date DATETIME NOT NULL, 
	course_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES course (id)
);
INSERT INTO "assignment" VALUES(1,'Student Grade Calculator','Question

Write a Java program that asks the user to enter two integers and then displays:

The sum of the two numbers.
The difference between the two numbers.
The product of the two numbers.
The quotient of the two numbers.','homework','2026-07-18 07:02:00.000000','2026-07-30 05:00:00.000000',1);
INSERT INTO "assignment" VALUES(2,'Mini Project: Library Book Management System','Project Description

Create a simple Java program that allows the user to manage books in a small library.

Features
Add a new book.
Display all books.
Search for a book by title.
Exit the program.
Requirements
Use a menu with switch.
Use arrays أو ArrayList (حسب ما درستم).
Use methods to organize the code.
Take input using Scanner.
Example Menu
===== Library Management System =====

1. Add Book
2. View Books
3. Search Book
4. Exit

Choose an option:','homework','2026-07-18 12:00:00.000000','2026-07-30 12:00:00.000000',1);
INSERT INTO "assignment" VALUES(3,'Quiz','Quiz 1- Ch1+2','quiz','2026-07-19 12:00:00.000000','2026-07-26 12:00:00.000000',1);
INSERT INTO "assignment" VALUES(4,'Quiz 2 - Short answer','Quiz 2 - Short answer','quiz','2026-07-20 12:00:00.000000','2026-07-27 12:00:00.000000',1);
INSERT INTO "assignment" VALUES(5,'Quiz 3 - Essay Quuestion','Quiz 2 - Essay Quuestion','quiz','2026-07-22 12:00:00.000000','2026-07-29 12:00:00.000000',1);
CREATE TABLE certificate (
	id INTEGER NOT NULL, 
	certificate_code VARCHAR(40) NOT NULL, 
	student_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	final_grade FLOAT NOT NULL, 
	issued_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_student_course_certificate UNIQUE (student_id, course_id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(course_id) REFERENCES course (id)
);
INSERT INTO "certificate" VALUES(1,'LRN-202607-5F48267B34',9,1,72.86,'2026-07-18 18:15:27.141278');
INSERT INTO "certificate" VALUES(2,'LRN-202607-DCDBCBB5DD',8,1,100.0,'2026-07-18 19:27:32.025117');
CREATE TABLE course (
	id INTEGER NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100), 
	description TEXT, 
	teacher_id INTEGER NOT NULL, 
	course_identifier VARCHAR(8) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_course_code UNIQUE (code), 
	FOREIGN KEY(teacher_id) REFERENCES user (id)
);
INSERT INTO "course" VALUES(1,'BSAI 1211','Programming (1)','',14,'SEG2');
CREATE TABLE discussion_like (
	id INTEGER NOT NULL, 
	topic_id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_topic_user_like UNIQUE (topic_id, user_id), 
	FOREIGN KEY(topic_id) REFERENCES discussion_topic (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);
CREATE TABLE discussion_post (
	id INTEGER NOT NULL, 
	topic_id INTEGER NOT NULL, 
	author_id INTEGER NOT NULL, 
	body TEXT NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, attachment_path VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(topic_id) REFERENCES discussion_topic (id), 
	FOREIGN KEY(author_id) REFERENCES user (id)
);
CREATE TABLE discussion_topic (
	id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	author_id INTEGER NOT NULL, 
	title VARCHAR(180) NOT NULL, 
	body TEXT NOT NULL, 
	is_pinned BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, topic_type VARCHAR(30) DEFAULT 'Discussion', is_locked BOOLEAN DEFAULT 0, attachment_path VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES course (id), 
	FOREIGN KEY(author_id) REFERENCES user (id)
);
INSERT INTO "discussion_topic" VALUES(1,1,8,'3','3',0,'2026-07-18 20:20:30.416773','2026-07-18 20:20:30.416773','Discussion',0,NULL);
CREATE TABLE enrollment (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(course_id) REFERENCES course (id)
);
INSERT INTO "enrollment" VALUES(1,8,1);
INSERT INTO "enrollment" VALUES(2,9,1);
INSERT INTO "enrollment" VALUES(3,10,1);
INSERT INTO "enrollment" VALUES(4,11,1);
INSERT INTO "enrollment" VALUES(5,12,1);
INSERT INTO "enrollment" VALUES(6,13,1);
CREATE TABLE exam (
	id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	description TEXT, 
	total_score FLOAT NOT NULL, 
	start_date DATETIME NOT NULL, 
	end_date DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES course (id)
);
INSERT INTO "exam" VALUES(2,1,'Final Exam','',60.0,'2026-07-19 09:00:00.000000','2026-07-19 16:00:00.000000');
CREATE TABLE exam_question (
	id INTEGER NOT NULL, 
	exam_id INTEGER NOT NULL, 
	question_text TEXT NOT NULL, 
	question_type VARCHAR(50) NOT NULL, 
	options TEXT, 
	answer TEXT NOT NULL, 
	score FLOAT NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(exam_id) REFERENCES exam (id)
);
INSERT INTO "exam_question" VALUES(11,2,'1. Which keyword is used to declare a class in Java?','mcq','A. object,B. class,C. define,D. public','B. class',6.0);
INSERT INTO "exam_question" VALUES(12,2,'2. Which method is the starting point of every Java program?','mcq','A. run(),B. start(),C. main(),D. execute()','C. main()',6.0);
INSERT INTO "exam_question" VALUES(13,2,'3. Which class is used to receive input from the user?','mcq','A. String,B. Scanner,C. Input,D. Console','B. Scanner',6.0);
INSERT INTO "exam_question" VALUES(14,2,'4. Which data type is used to store decimal numbers?','mcq','A. int,B. char,C. double,D. boolean','C. double',6.0);
INSERT INTO "exam_question" VALUES(15,2,'5. Which statement prints text and moves to the next line?','mcq','A. System.out.print(),B. System.out.println(),C. print(),D. display()','B. System.out.println()',6.0);
INSERT INTO "exam_question" VALUES(16,2,'6. Which operator is used for multiplication?','mcq','A. +,B. -,C. *,D. /','C. *',6.0);
INSERT INTO "exam_question" VALUES(17,2,'7. Java is an object-oriented programming language.','true_false','True,False','True',6.0);
INSERT INTO "exam_question" VALUES(18,2,'8.he Scanner class is used to print output.','true_false','True,False','False',6.0);
INSERT INTO "exam_question" VALUES(19,2,'9.Variable names in Java can start with a number.','true_false','True,False','True',6.0);
INSERT INTO "exam_question" VALUES(20,2,'10. The println() method prints output and moves to a new line.','true_false','True,False','True',6.0);
CREATE TABLE grade (
	id INTEGER NOT NULL, 
	exam_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	score FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(exam_id) REFERENCES exam (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
);
INSERT INTO "grade" VALUES(1,2,9,54.0);
CREATE TABLE notification (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	title VARCHAR(160) NOT NULL, 
	message TEXT NOT NULL, 
	link VARCHAR(255), 
	is_read BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id)
);
INSERT INTO "notification" VALUES(1,8,'New learning unit','A new unit “Topic 1” was added to Programming (1).','/student/courses/1',0,'2026-07-18 17:59:48.649308');
INSERT INTO "notification" VALUES(2,9,'New learning unit','A new unit “Topic 1” was added to Programming (1).','/student/courses/1',0,'2026-07-18 17:59:48.649308');
INSERT INTO "notification" VALUES(3,10,'New learning unit','A new unit “Topic 1” was added to Programming (1).','/student/courses/1',0,'2026-07-18 17:59:48.649308');
INSERT INTO "notification" VALUES(4,11,'New learning unit','A new unit “Topic 1” was added to Programming (1).','/student/courses/1',0,'2026-07-18 17:59:48.649308');
INSERT INTO "notification" VALUES(5,12,'New learning unit','A new unit “Topic 1” was added to Programming (1).','/student/courses/1',0,'2026-07-18 17:59:48.649308');
INSERT INTO "notification" VALUES(6,13,'New learning unit','A new unit “Topic 1” was added to Programming (1).','/student/courses/1',0,'2026-07-18 17:59:48.649308');
INSERT INTO "notification" VALUES(7,8,'New exam','‘Final Exams’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:04:25.424468');
INSERT INTO "notification" VALUES(8,9,'New exam','‘Final Exams’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:04:25.424468');
INSERT INTO "notification" VALUES(9,10,'New exam','‘Final Exams’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:04:25.424468');
INSERT INTO "notification" VALUES(10,11,'New exam','‘Final Exams’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:04:25.424468');
INSERT INTO "notification" VALUES(11,12,'New exam','‘Final Exams’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:04:25.424468');
INSERT INTO "notification" VALUES(12,13,'New exam','‘Final Exams’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:04:25.424468');
INSERT INTO "notification" VALUES(13,8,'New assignment','‘Assignment 1’ was added to Programming (1). Due: 21 Jul 2026 21:12.','/student/courses/1',0,'2026-07-18 18:12:16.431201');
INSERT INTO "notification" VALUES(14,9,'New assignment','‘Assignment 1’ was added to Programming (1). Due: 21 Jul 2026 21:12.','/student/courses/1',0,'2026-07-18 18:12:16.431201');
INSERT INTO "notification" VALUES(15,10,'New assignment','‘Assignment 1’ was added to Programming (1). Due: 21 Jul 2026 21:12.','/student/courses/1',0,'2026-07-18 18:12:16.431201');
INSERT INTO "notification" VALUES(16,11,'New assignment','‘Assignment 1’ was added to Programming (1). Due: 21 Jul 2026 21:12.','/student/courses/1',0,'2026-07-18 18:12:16.431201');
INSERT INTO "notification" VALUES(17,12,'New assignment','‘Assignment 1’ was added to Programming (1). Due: 21 Jul 2026 21:12.','/student/courses/1',0,'2026-07-18 18:12:16.431201');
INSERT INTO "notification" VALUES(18,13,'New assignment','‘Assignment 1’ was added to Programming (1). Due: 21 Jul 2026 21:12.','/student/courses/1',0,'2026-07-18 18:12:16.431201');
INSERT INTO "notification" VALUES(19,9,'Assignment graded','Your submission for Assignment 1 received 100.0/100.','/student/courses/1',0,'2026-07-18 18:14:10.135993');
INSERT INTO "notification" VALUES(20,9,'Certificate Available','Congratulations! Your certificate for Programming (1) is ready.','/student/certificate/1',0,'2026-07-18 18:15:27.148040');
INSERT INTO "notification" VALUES(21,8,'New quiz','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:28:14.100819');
INSERT INTO "notification" VALUES(22,9,'New quiz','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:28:14.102205');
INSERT INTO "notification" VALUES(23,10,'New quiz','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:28:14.102205');
INSERT INTO "notification" VALUES(24,11,'New quiz','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:28:14.102205');
INSERT INTO "notification" VALUES(25,12,'New quiz','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:28:14.102205');
INSERT INTO "notification" VALUES(26,13,'New quiz','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:28:14.102205');
INSERT INTO "notification" VALUES(27,8,'New quiz','‘س’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:38:47.129108');
INSERT INTO "notification" VALUES(28,9,'New quiz','‘س’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:38:47.129108');
INSERT INTO "notification" VALUES(29,10,'New quiz','‘س’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:38:47.129108');
INSERT INTO "notification" VALUES(30,11,'New quiz','‘س’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:38:47.129108');
INSERT INTO "notification" VALUES(31,12,'New quiz','‘س’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:38:47.129108');
INSERT INTO "notification" VALUES(32,13,'New quiz','‘س’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:38:47.129108');
INSERT INTO "notification" VALUES(33,8,'New quiz','‘الكويز 2’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:39:29.864315');
INSERT INTO "notification" VALUES(34,9,'New quiz','‘الكويز 2’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:39:29.864315');
INSERT INTO "notification" VALUES(35,10,'New quiz','‘الكويز 2’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:39:29.864315');
INSERT INTO "notification" VALUES(36,11,'New quiz','‘الكويز 2’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:39:29.864315');
INSERT INTO "notification" VALUES(37,12,'New quiz','‘الكويز 2’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:39:29.864315');
INSERT INTO "notification" VALUES(38,13,'New quiz','‘الكويز 2’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:39:29.864315');
INSERT INTO "notification" VALUES(39,8,'New exam','‘النهائي’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:44:35.052381');
INSERT INTO "notification" VALUES(40,9,'New exam','‘النهائي’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:44:35.052381');
INSERT INTO "notification" VALUES(41,10,'New exam','‘النهائي’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:44:35.052381');
INSERT INTO "notification" VALUES(42,11,'New exam','‘النهائي’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:44:35.052381');
INSERT INTO "notification" VALUES(43,12,'New exam','‘النهائي’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:44:35.052381');
INSERT INTO "notification" VALUES(44,13,'New exam','‘النهائي’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:44:35.052381');
INSERT INTO "notification" VALUES(45,8,'New exam','‘كويز 4’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:46:06.527654');
INSERT INTO "notification" VALUES(46,9,'New exam','‘كويز 4’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:46:06.527654');
INSERT INTO "notification" VALUES(47,10,'New exam','‘كويز 4’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:46:06.527654');
INSERT INTO "notification" VALUES(48,11,'New exam','‘كويز 4’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:46:06.527654');
INSERT INTO "notification" VALUES(49,12,'New exam','‘كويز 4’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:46:06.527654');
INSERT INTO "notification" VALUES(50,13,'New exam','‘كويز 4’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 18:46:06.527654');
INSERT INTO "notification" VALUES(51,8,'New exam','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:15:26.605980');
INSERT INTO "notification" VALUES(52,9,'New exam','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:15:26.605980');
INSERT INTO "notification" VALUES(53,10,'New exam','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:15:26.605980');
INSERT INTO "notification" VALUES(54,11,'New exam','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:15:26.605980');
INSERT INTO "notification" VALUES(55,12,'New exam','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:15:26.605980');
INSERT INTO "notification" VALUES(56,13,'New exam','‘Quiz 1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:15:26.605980');
INSERT INTO "notification" VALUES(57,8,'New exam','‘Qiz 15’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:16:40.715026');
INSERT INTO "notification" VALUES(58,9,'New exam','‘Qiz 15’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:16:40.715026');
INSERT INTO "notification" VALUES(59,10,'New exam','‘Qiz 15’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:16:40.715026');
INSERT INTO "notification" VALUES(60,11,'New exam','‘Qiz 15’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:16:40.715026');
INSERT INTO "notification" VALUES(61,12,'New exam','‘Qiz 15’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:16:40.715026');
INSERT INTO "notification" VALUES(62,13,'New exam','‘Qiz 15’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:16:40.715026');
INSERT INTO "notification" VALUES(63,8,'New quiz','‘test1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:17:46.913569');
INSERT INTO "notification" VALUES(64,9,'New quiz','‘test1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:17:46.913569');
INSERT INTO "notification" VALUES(65,10,'New quiz','‘test1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:17:46.913569');
INSERT INTO "notification" VALUES(66,11,'New quiz','‘test1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:17:46.913569');
INSERT INTO "notification" VALUES(67,12,'New quiz','‘test1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:17:46.913569');
INSERT INTO "notification" VALUES(68,13,'New quiz','‘test1’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:17:46.913569');
INSERT INTO "notification" VALUES(69,8,'Certificate Available','Congratulations! Your certificate for Programming (1) is ready.','/student/certificate/1',0,'2026-07-18 19:27:32.031357');
INSERT INTO "notification" VALUES(70,8,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:30:47.565274');
INSERT INTO "notification" VALUES(71,9,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:30:47.565274');
INSERT INTO "notification" VALUES(72,10,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:30:47.565274');
INSERT INTO "notification" VALUES(73,11,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:30:47.565274');
INSERT INTO "notification" VALUES(74,12,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:30:47.565274');
INSERT INTO "notification" VALUES(75,13,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-18 19:30:47.565274');
INSERT INTO "notification" VALUES(76,8,'New discussion','Ahmed Ali Hassan: 3','/forum/topic/1',0,'2026-07-18 20:20:30.437803');
INSERT INTO "notification" VALUES(77,9,'New discussion','Ahmed Ali Hassan: 3','/forum/topic/1',0,'2026-07-18 20:20:30.437803');
INSERT INTO "notification" VALUES(78,10,'New discussion','Ahmed Ali Hassan: 3','/forum/topic/1',0,'2026-07-18 20:20:30.437803');
INSERT INTO "notification" VALUES(79,11,'New discussion','Ahmed Ali Hassan: 3','/forum/topic/1',0,'2026-07-18 20:20:30.437803');
INSERT INTO "notification" VALUES(80,12,'New discussion','Ahmed Ali Hassan: 3','/forum/topic/1',0,'2026-07-18 20:20:30.437803');
INSERT INTO "notification" VALUES(81,13,'New discussion','Ahmed Ali Hassan: 3','/forum/topic/1',0,'2026-07-18 20:20:30.437803');
INSERT INTO "notification" VALUES(82,8,'New learning unit','A new unit “ch01” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:48:41.944597');
INSERT INTO "notification" VALUES(83,9,'New learning unit','A new unit “ch01” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:48:41.944597');
INSERT INTO "notification" VALUES(84,10,'New learning unit','A new unit “ch01” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:48:41.944597');
INSERT INTO "notification" VALUES(85,11,'New learning unit','A new unit “ch01” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:48:41.944597');
INSERT INTO "notification" VALUES(86,12,'New learning unit','A new unit “ch01” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:48:41.944597');
INSERT INTO "notification" VALUES(87,13,'New learning unit','A new unit “ch01” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:48:41.944597');
INSERT INTO "notification" VALUES(88,8,'New learning unit','A new unit “ch2-part1” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:08.044691');
INSERT INTO "notification" VALUES(89,9,'New learning unit','A new unit “ch2-part1” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:08.044691');
INSERT INTO "notification" VALUES(90,10,'New learning unit','A new unit “ch2-part1” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:08.044691');
INSERT INTO "notification" VALUES(91,11,'New learning unit','A new unit “ch2-part1” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:08.044691');
INSERT INTO "notification" VALUES(92,12,'New learning unit','A new unit “ch2-part1” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:08.044691');
INSERT INTO "notification" VALUES(93,13,'New learning unit','A new unit “ch2-part1” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:08.044691');
INSERT INTO "notification" VALUES(94,8,'New learning unit','A new unit “ch2-part2” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:30.732633');
INSERT INTO "notification" VALUES(95,9,'New learning unit','A new unit “ch2-part2” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:30.732633');
INSERT INTO "notification" VALUES(96,10,'New learning unit','A new unit “ch2-part2” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:30.732633');
INSERT INTO "notification" VALUES(97,11,'New learning unit','A new unit “ch2-part2” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:30.732633');
INSERT INTO "notification" VALUES(98,12,'New learning unit','A new unit “ch2-part2” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:30.732633');
INSERT INTO "notification" VALUES(99,13,'New learning unit','A new unit “ch2-part2” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:49:30.732633');
INSERT INTO "notification" VALUES(100,8,'New learning unit','A new unit “ch04” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:50:04.978131');
INSERT INTO "notification" VALUES(101,9,'New learning unit','A new unit “ch04” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:50:04.978131');
INSERT INTO "notification" VALUES(102,10,'New learning unit','A new unit “ch04” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:50:04.978131');
INSERT INTO "notification" VALUES(103,11,'New learning unit','A new unit “ch04” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:50:04.978131');
INSERT INTO "notification" VALUES(104,12,'New learning unit','A new unit “ch04” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:50:04.978131');
INSERT INTO "notification" VALUES(105,13,'New learning unit','A new unit “ch04” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:50:04.978131');
INSERT INTO "notification" VALUES(106,8,'New learning unit','A new unit “ch05” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:04.483294');
INSERT INTO "notification" VALUES(107,9,'New learning unit','A new unit “ch05” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:04.483294');
INSERT INTO "notification" VALUES(108,10,'New learning unit','A new unit “ch05” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:04.483294');
INSERT INTO "notification" VALUES(109,11,'New learning unit','A new unit “ch05” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:04.483294');
INSERT INTO "notification" VALUES(110,12,'New learning unit','A new unit “ch05” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:04.483294');
INSERT INTO "notification" VALUES(111,13,'New learning unit','A new unit “ch05” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:04.483294');
INSERT INTO "notification" VALUES(112,8,'New learning unit','A new unit “ch06” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:26.894056');
INSERT INTO "notification" VALUES(113,9,'New learning unit','A new unit “ch06” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:26.894056');
INSERT INTO "notification" VALUES(114,10,'New learning unit','A new unit “ch06” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:26.894056');
INSERT INTO "notification" VALUES(115,11,'New learning unit','A new unit “ch06” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:26.894056');
INSERT INTO "notification" VALUES(116,12,'New learning unit','A new unit “ch06” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:26.894056');
INSERT INTO "notification" VALUES(117,13,'New learning unit','A new unit “ch06” was added to Programming (1).','/student/courses/1',0,'2026-07-19 07:51:26.894056');
INSERT INTO "notification" VALUES(118,8,'New assignment','‘Student Grade Calculator’ was added to Programming (1). Due: 30 Jul 2026 05:00.','/student/courses/1',0,'2026-07-19 07:55:20.725057');
INSERT INTO "notification" VALUES(119,9,'New assignment','‘Student Grade Calculator’ was added to Programming (1). Due: 30 Jul 2026 05:00.','/student/courses/1',0,'2026-07-19 07:55:20.725057');
INSERT INTO "notification" VALUES(120,10,'New assignment','‘Student Grade Calculator’ was added to Programming (1). Due: 30 Jul 2026 05:00.','/student/courses/1',0,'2026-07-19 07:55:20.725057');
INSERT INTO "notification" VALUES(121,11,'New assignment','‘Student Grade Calculator’ was added to Programming (1). Due: 30 Jul 2026 05:00.','/student/courses/1',0,'2026-07-19 07:55:20.725057');
INSERT INTO "notification" VALUES(122,12,'New assignment','‘Student Grade Calculator’ was added to Programming (1). Due: 30 Jul 2026 05:00.','/student/courses/1',0,'2026-07-19 07:55:20.725057');
INSERT INTO "notification" VALUES(123,13,'New assignment','‘Student Grade Calculator’ was added to Programming (1). Due: 30 Jul 2026 05:00.','/student/courses/1',0,'2026-07-19 07:55:20.725057');
INSERT INTO "notification" VALUES(124,8,'New assignment','‘Mini Project: Library Book Management System’ was added to Programming (1). Due: 30 Jul 2026 12:00.','/student/courses/1',0,'2026-07-19 07:57:38.671945');
INSERT INTO "notification" VALUES(125,9,'New assignment','‘Mini Project: Library Book Management System’ was added to Programming (1). Due: 30 Jul 2026 12:00.','/student/courses/1',0,'2026-07-19 07:57:38.671945');
INSERT INTO "notification" VALUES(126,10,'New assignment','‘Mini Project: Library Book Management System’ was added to Programming (1). Due: 30 Jul 2026 12:00.','/student/courses/1',0,'2026-07-19 07:57:38.671945');
INSERT INTO "notification" VALUES(127,11,'New assignment','‘Mini Project: Library Book Management System’ was added to Programming (1). Due: 30 Jul 2026 12:00.','/student/courses/1',0,'2026-07-19 07:57:38.671945');
INSERT INTO "notification" VALUES(128,12,'New assignment','‘Mini Project: Library Book Management System’ was added to Programming (1). Due: 30 Jul 2026 12:00.','/student/courses/1',0,'2026-07-19 07:57:38.671945');
INSERT INTO "notification" VALUES(129,13,'New assignment','‘Mini Project: Library Book Management System’ was added to Programming (1). Due: 30 Jul 2026 12:00.','/student/courses/1',0,'2026-07-19 07:57:38.671945');
INSERT INTO "notification" VALUES(130,8,'New quiz','‘Quiz’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:02:28.550730');
INSERT INTO "notification" VALUES(131,9,'New quiz','‘Quiz’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:02:28.550730');
INSERT INTO "notification" VALUES(132,10,'New quiz','‘Quiz’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:02:28.550730');
INSERT INTO "notification" VALUES(133,11,'New quiz','‘Quiz’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:02:28.550730');
INSERT INTO "notification" VALUES(134,12,'New quiz','‘Quiz’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:02:28.550730');
INSERT INTO "notification" VALUES(135,13,'New quiz','‘Quiz’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:02:28.550730');
INSERT INTO "notification" VALUES(136,8,'New quiz','‘Quiz 2 - Short answer’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:05:10.538725');
INSERT INTO "notification" VALUES(137,9,'New quiz','‘Quiz 2 - Short answer’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:05:10.538725');
INSERT INTO "notification" VALUES(138,10,'New quiz','‘Quiz 2 - Short answer’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:05:10.538725');
INSERT INTO "notification" VALUES(139,11,'New quiz','‘Quiz 2 - Short answer’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:05:10.538725');
INSERT INTO "notification" VALUES(140,12,'New quiz','‘Quiz 2 - Short answer’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:05:10.538725');
INSERT INTO "notification" VALUES(141,13,'New quiz','‘Quiz 2 - Short answer’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:05:10.538725');
INSERT INTO "notification" VALUES(142,8,'New quiz','‘Quiz 3 - Essay Quuestion’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:06:34.129514');
INSERT INTO "notification" VALUES(143,9,'New quiz','‘Quiz 3 - Essay Quuestion’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:06:34.129514');
INSERT INTO "notification" VALUES(144,10,'New quiz','‘Quiz 3 - Essay Quuestion’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:06:34.129514');
INSERT INTO "notification" VALUES(145,11,'New quiz','‘Quiz 3 - Essay Quuestion’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:06:34.129514');
INSERT INTO "notification" VALUES(146,12,'New quiz','‘Quiz 3 - Essay Quuestion’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:06:34.129514');
INSERT INTO "notification" VALUES(147,13,'New quiz','‘Quiz 3 - Essay Quuestion’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:06:34.129514');
INSERT INTO "notification" VALUES(148,8,'New exam','‘Midterm Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:11:24.556203');
INSERT INTO "notification" VALUES(149,9,'New exam','‘Midterm Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:11:24.556203');
INSERT INTO "notification" VALUES(150,10,'New exam','‘Midterm Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:11:24.556203');
INSERT INTO "notification" VALUES(151,11,'New exam','‘Midterm Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:11:24.556203');
INSERT INTO "notification" VALUES(152,12,'New exam','‘Midterm Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:11:24.556203');
INSERT INTO "notification" VALUES(153,13,'New exam','‘Midterm Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:11:24.556203');
INSERT INTO "notification" VALUES(154,8,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:16:40.805440');
INSERT INTO "notification" VALUES(155,9,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:16:40.805440');
INSERT INTO "notification" VALUES(156,10,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:16:40.805440');
INSERT INTO "notification" VALUES(157,11,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:16:40.805440');
INSERT INTO "notification" VALUES(158,12,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:16:40.805440');
INSERT INTO "notification" VALUES(159,13,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 08:16:40.805440');
INSERT INTO "notification" VALUES(160,8,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:00:22.901771');
INSERT INTO "notification" VALUES(161,9,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:00:22.901771');
INSERT INTO "notification" VALUES(162,10,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:00:22.901771');
INSERT INTO "notification" VALUES(163,11,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:00:22.901771');
INSERT INTO "notification" VALUES(164,12,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:00:22.901771');
INSERT INTO "notification" VALUES(165,13,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:00:22.901771');
INSERT INTO "notification" VALUES(166,8,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:13:51.459994');
INSERT INTO "notification" VALUES(167,9,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:13:51.459994');
INSERT INTO "notification" VALUES(168,10,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:13:51.459994');
INSERT INTO "notification" VALUES(169,11,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:13:51.459994');
INSERT INTO "notification" VALUES(170,12,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:13:51.459994');
INSERT INTO "notification" VALUES(171,13,'New exam','‘Final Exam’ is now available in Programming (1).','/student/courses/1',0,'2026-07-19 09:13:51.459994');
CREATE TABLE quiz (
	id INTEGER NOT NULL, 
	assignment_id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	description TEXT, 
	start_date DATETIME NOT NULL, 
	end_date DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (assignment_id), 
	FOREIGN KEY(assignment_id) REFERENCES assignment (id), 
	FOREIGN KEY(course_id) REFERENCES course (id)
);
INSERT INTO "quiz" VALUES(1,3,1,'Quiz','Quiz 1- Ch1+2','2026-07-19 12:00:00.000000','2026-07-26 12:00:00.000000');
INSERT INTO "quiz" VALUES(2,4,1,'Quiz 2 - Short answer','Quiz 2 - Short answer','2026-07-20 12:00:00.000000','2026-07-27 12:00:00.000000');
INSERT INTO "quiz" VALUES(3,5,1,'Quiz 3 - Essay Quuestion','Quiz 2 - Essay Quuestion','2026-07-22 12:00:00.000000','2026-07-29 12:00:00.000000');
CREATE TABLE quiz_question (
	id INTEGER NOT NULL, 
	quiz_id INTEGER NOT NULL, 
	question_text TEXT NOT NULL, 
	question_type VARCHAR(50) NOT NULL, 
	options TEXT, 
	answer TEXT NOT NULL, 
	score INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(quiz_id) REFERENCES quiz (id)
);
INSERT INTO "quiz_question" VALUES(1,1,'1. Which class is used to take input from the user in Java?','mcq','A. System,B. Scanner,C. String,D. PrintWriter','B. Scanner',1);
INSERT INTO "quiz_question" VALUES(2,1,'2. Which data type is used to store decimal numbers?','mcq','A. int,B. char,C. double,D. boolean','C. double',1);
INSERT INTO "quiz_question" VALUES(3,1,'4. Which method is used to print output with a new line?','mcq','A. print(),B. println(),C. input(),D. scanf()','B. println()',1);
INSERT INTO "quiz_question" VALUES(4,1,'3. Which symbol is used to end a statement in Java?','mcq','A. :,B. .,C. ;..,D. ;','D. ;',1);
INSERT INTO "quiz_question" VALUES(5,2,'Write the Java statement to declare an integer variable named age.','short_answer','','int age;',1);
INSERT INTO "quiz_question" VALUES(6,2,'What is the output statement used in Java?','short_answer','','System.out.println();',1);
INSERT INTO "quiz_question" VALUES(7,3,'Explain the difference between print() and println() in Java.','essay','','Manual grading required',1);
INSERT INTO "quiz_question" VALUES(8,3,'Explain why variables are important in Java programs.','essay','','Manual grading required',1);
CREATE TABLE submission (
	id INTEGER NOT NULL, 
	assignment_id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	submission_text TEXT, 
	submission_file VARCHAR(200), 
	grade FLOAT, 
	feedback TEXT, 
	submitted_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(assignment_id) REFERENCES assignment (id), 
	FOREIGN KEY(student_id) REFERENCES user (id)
);
INSERT INTO "submission" VALUES(1,1,9,'import java.util.Scanner;

public class ArithmeticOperations {
    public static void main(String[] args) {
        Scanner input = new Scanner(System.in);

        // Read two integers
        System.out.print("Enter the first integer: ");
        int num1 = input.nextInt();

        System.out.print("Enter the second integer: ");
        int num2 = input.nextInt();

        // Display results
        System.out.println("Sum = " + (num1 + num2));
        System.out.println("Difference = " + (num1 - num2));
        System.out.println("Product = " + (num1 * num2));

        if (num2 != 0) {
            System.out.println("Quotient = " + (num1 / num2));
        } else {
            System.out.println("Quotient = Cannot divide by zero.");
        }

        input.close();
    }
}',NULL,NULL,NULL,'2026-07-19 08:42:25.859996');
INSERT INTO "submission" VALUES(2,3,9,'{"1": "B. Scanner", "2": "C. double", "3": "B. println()", "4": "D. ;"}',NULL,4.0,NULL,'2026-07-19 08:44:09.623050');
INSERT INTO "submission" VALUES(3,5,9,'{"7": "print() displays the output on the same line without moving to a new line. println() displays the output and then moves the cursor to the next line, so the next output appears on a new line.", "8": "Variables are important because they store data that the program uses. They make it easy to save, update, and work with values during program execution."}',NULL,0.0,NULL,'2026-07-19 08:48:38.266541');
INSERT INTO "submission" VALUES(4,4,9,'{"5": "int age;", "6": "The output statement used in Java is System.out.println() or System.out.print(). It is used to display text or values on the screen."}',NULL,1.0,NULL,'2026-07-19 08:49:35.034219');
CREATE TABLE unit (
	id INTEGER NOT NULL, 
	course_id INTEGER NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	content TEXT, 
	file_path VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(course_id) REFERENCES course (id)
);
INSERT INTO "unit" VALUES(1,1,'ch01',NULL,'608a2237c9ed49aca376adbc1e0b5509_ch01.ppt');
INSERT INTO "unit" VALUES(2,1,'ch2-part1',NULL,'98d901feff8a45a8a4b3b36410246ad3_ch2-part1.ppt');
INSERT INTO "unit" VALUES(3,1,'ch2-part2',NULL,'511a33f318644f1db77ae52456f8bca5_ch2-part2.ppt');
INSERT INTO "unit" VALUES(4,1,'ch04',NULL,'5dd2159818c2437cb222275479fcc77c_ch04.ppt');
INSERT INTO "unit" VALUES(5,1,'ch05',NULL,'ee90b4e5a19f42398ac5aebd4e2c3781_Chapter_5.ppt');
INSERT INTO "unit" VALUES(6,1,'ch06',NULL,'ed174b3f7b3d439892d803eaf7ea0410_ch06.ppt');
CREATE TABLE unit_completion (
	id INTEGER NOT NULL, 
	student_id INTEGER NOT NULL, 
	unit_id INTEGER NOT NULL, 
	completed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_unit_completion UNIQUE (student_id, unit_id), 
	FOREIGN KEY(student_id) REFERENCES user (id), 
	FOREIGN KEY(unit_id) REFERENCES unit (id)
);
INSERT INTO "unit_completion" VALUES(1,9,4,'2026-07-19 08:41:39.138092');
INSERT INTO "unit_completion" VALUES(2,9,1,'2026-07-19 08:41:41.175079');
INSERT INTO "unit_completion" VALUES(3,9,5,'2026-07-19 08:41:42.225898');
INSERT INTO "unit_completion" VALUES(4,9,6,'2026-07-19 08:41:43.421503');
INSERT INTO "unit_completion" VALUES(5,9,2,'2026-07-19 08:41:44.897175');
INSERT INTO "unit_completion" VALUES(6,9,3,'2026-07-19 08:41:46.361291');
CREATE TABLE user (
	id INTEGER NOT NULL, 
	username VARCHAR(50) NOT NULL, 
	email VARCHAR(100) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(10) NOT NULL, name_person VARCHAR(100), university_id VARCHAR(30), employee_id VARCHAR(30), phone VARCHAR(25), department VARCHAR(100), level VARCHAR(30), gender VARCHAR(15), status VARCHAR(20) DEFAULT 'Active', office_number VARCHAR(30), academic_rank VARCHAR(60), visible_password VARCHAR(255), 
	PRIMARY KEY (id)
);
INSERT INTO "user" VALUES(7,'admin','admin@ecms.com','15','admin',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'Active',NULL,NULL,NULL);
INSERT INTO "user" VALUES(8,'ahmed.ali','ahmed.ali@learnova.edu','scrypt:32768:8:1$12bFacGG7rbahGej$2b409c89cb22410a1d2f6c254a19c801ebea22738c6073215b58ff85ed0127bc0f5c8b711cf46c8b9deaf0788ee61923b0813a8696f79c5c4b8cf006ffd10e75','student','Ahmed Ali Hassan','20261001',NULL,'+972501234001','Computer Science','Year 1','Male','Active',NULL,NULL,'ahmed.ali@123');
INSERT INTO "user" VALUES(9,'sara.omar','sara.omar@learnova.edu','scrypt:32768:8:1$XGLrurLkGrkNzfWw$72fec392e720e76beffd2148ea755ea7f9334988d272b75d6d047d6a179bcad461d0f1b94d36af10bdb2717f1a2f87f00280da7877529269af6e502f57c92e77','student','Sara Mohammed Omar','20261002',NULL,'+972501234002','Software Engineering','Year 2','Female','Active',NULL,NULL,'sara.omar@25874');
INSERT INTO "user" VALUES(10,'omar.salem','omar.salem@learnova.edu','scrypt:32768:8:1$eSWOCNPUQ3xfwVop$d6266fb925ceac70380ef30d808a8cc69aa4899cbb185b5fb4cb44469ad5cba51553b14379379b8c29730c30c67b4ebe15629f358f2e3881a533f06ded01bb84','student','Omar Khaled Salem','20261003',NULL,'+972501234003','Artificial Intelligence','Year 3','Male','Active',NULL,NULL,'omar.salem@7466');
INSERT INTO "user" VALUES(11,'aya.faris','aya.faris@learnova.edu','scrypt:32768:8:1$5vJbDoBDkijNTSPW$aac65a097524ec2a71d3997b2041e74db02fb1f25d4bd467ad8faed08d2db267c1a847fd1aadecd1e4cb4dff12fd52cccea3dcd0f5f53a7d4c4501ea660e2a4b','student','Aya Mahmoud Faris','20261008',NULL,'+972501234008','Information Technology','Year 1','Male','Active',NULL,NULL,'aya.faris@65');
INSERT INTO "user" VALUES(12,'noor.yasin','noor.yasin@learnova.edu','scrypt:32768:8:1$MZp40iKL3UprzAWN$0e754a6d716223fbbf01d15cd588048a7f4ff852574f09f3e6bc00716e2ea584f4958d2eb65005d08a9f4e18378536d69dc914d1d4cec204fb57daaa5ff36ba3','student','Noor Ahmad Yasin','20261004',NULL,'+972501234004','Cyber Security','Year 2','Female','Active',NULL,NULL,'noor.yasin@697');
INSERT INTO "user" VALUES(13,'dana.mustafa','dana.mustafa@learnova.edu','scrypt:32768:8:1$9V0Cr8rnew4R4zAM$0ba9e09cb8a390025e1e8a0af9297e2c2281db1ec6e11e31bb3f4661de5a90684a432dafaf8329bd5a49dff31bc60267b1e4fbaf3eded69646abfd07bb26f30b','student','Dana Ali Mustafa','20261010',NULL,'+972501234008','Business','Year 4','Female','Active',NULL,NULL,'dana.mustafa@874');
INSERT INTO "user" VALUES(14,'l.samhan','l.samhan@up.edu.ps','scrypt:32768:8:1$oydvpfTe1IvcACoj$d3e693e264d8ab488f74922027fa111aedbc1a2ad8f7c0448340d64566456e56b71d518c432c4cb1d6e8462502d491480042e5f5eb51bea012dff7e8663164ef','teacher','Lecturer: lamis samhan',NULL,'1258746','+972 59-259-7056','Software Engineering',NULL,'Female','Active','None','Lecturer','l.samhan@64756');
CREATE UNIQUE INDEX ix_user_username ON user (username);
CREATE UNIQUE INDEX ix_user_email ON user (email);
CREATE UNIQUE INDEX ix_course_course_identifier ON course (course_identifier);
CREATE UNIQUE INDEX ix_course_code ON course (code);
CREATE INDEX ix_unit_completion_unit_id ON unit_completion (unit_id);
CREATE INDEX ix_unit_completion_student_id ON unit_completion (student_id);
CREATE INDEX ix_notification_user_id ON notification (user_id);
CREATE INDEX ix_certificate_course_id ON certificate (course_id);
CREATE INDEX ix_certificate_student_id ON certificate (student_id);
CREATE UNIQUE INDEX ix_certificate_certificate_code ON certificate (certificate_code);
CREATE INDEX ix_discussion_topic_author_id ON discussion_topic (author_id);
CREATE INDEX ix_discussion_topic_course_id ON discussion_topic (course_id);
CREATE INDEX ix_discussion_post_author_id ON discussion_post (author_id);
CREATE INDEX ix_discussion_post_topic_id ON discussion_post (topic_id);
CREATE INDEX ix_discussion_like_topic_id ON discussion_like (topic_id);
CREATE INDEX ix_discussion_like_user_id ON discussion_like (user_id);
COMMIT;