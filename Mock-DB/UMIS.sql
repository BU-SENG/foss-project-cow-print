-- Create Database
CREATE DATABASE UMIS;
USE UMIS;

-- Create tables with initial definitions and primary and foreign keys constraints
CREATE TABLE student (
    student_id INT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email_address VARCHAR(50),
    address VARCHAR(50),
    phone_no VARCHAR(20)
);

CREATE TABLE faculty (
    faculty_id INT PRIMARY KEY,
    faculty_name VARCHAR(30),
    email VARCHAR(50),
    phone_no VARCHAR(20)
);

CREATE TABLE department (
    department_id INT PRIMARY KEY,
    department_name VARCHAR(30),
    faculty_id INT,
    FOREIGN KEY (faculty_id) REFERENCES faculty(faculty_id)
);

CREATE TABLE courses (
    course_id INT PRIMARY KEY,
    course_name VARCHAR(50),
    course_desc VARCHAR(40),
    credit_hours INT,
    prerequisite VARCHAR(40),
    department_id INT,
    FOREIGN KEY (department_id) REFERENCES department(department_id)
);

CREATE TABLE teacher (
    teacher_id INT PRIMARY KEY,
    first_name VARCHAR(30),
    last_name VARCHAR(30),
    email VARCHAR(30),
    qualification VARCHAR(30),
    department_id INT,
    FOREIGN KEY (department_id) REFERENCES department(department_id)
);

CREATE TABLE classroom (
    classroom_id INT PRIMARY KEY,
    room_no INT,
    capacity INT,
    building VARCHAR(30)
);

CREATE TABLE class_schedule (
    schedule_id INT PRIMARY KEY,
    class_day VARCHAR(30),
    start_time TIME,
    end_time TIME,
    course_id INT,
    classroom_id INT,
    teacher_id INT,
    FOREIGN KEY (course_id) REFERENCES courses(course_id),
    FOREIGN KEY (classroom_id) REFERENCES classroom(classroom_id),
    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id)
);

CREATE TABLE payment (
    payment_id INT PRIMARY KEY,
    payment_date DATE,
    amount INT,
    payment_status VARCHAR(10),
    payment_method VARCHAR(20),
    student_id INT,
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);

CREATE TABLE enrollment (
    enrollment_id INT PRIMARY KEY,
    enrollment_date DATE,
    grade VARCHAR(5),
    enrollment_status VARCHAR(30),
    student_id INT,
    course_id INT,
    FOREIGN KEY (student_id) REFERENCES student(student_id),
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);

CREATE TABLE exam (
    exam_id INT PRIMARY KEY,
    exam_date DATE,
    start_time TIME,
    end_time TIME,
    location VARCHAR(20),
    course_id INT,
    FOREIGN KEY (course_id) REFERENCES courses(course_id)
);
-- NOT NULL CONSTRAINT
ALTER TABLE student MODIFY first_name VARCHAR(50) NOT NULL;
ALTER TABLE student MODIFY last_name VARCHAR(50) NOT NULL;
ALTER TABLE payment MODIFY payment_method VARCHAR(20) NOT NULL;
ALTER TABLE student MODIFY student_id INT NOT NULL;
ALTER TABLE teacher MODIFY teacher_id INT NOT NULL;
ALTER TABLE teacher MODIFY first_name VARCHAR(30) NOT NULL;
ALTER TABLE teacher MODIFY last_name VARCHAR(30) NOT NULL;
ALTER TABLE courses MODIFY course_id INT NOT NULL;
ALTER TABLE courses MODIFY course_name VARCHAR(50) NOT NULL;
-- CHECK CONSTRAINT 
ALTER TABLE payment ADD CONSTRAINT chk_payment_status CHECK (payment_status IN ('Paid', 'Unpaid'));
ALTER TABLE enrollment ADD CONSTRAINT chk_enrollment_status CHECK (enrollment_status IN ('ACTIVE', 'INACTIVE'));

-- UNIQUE CONSTRAINT
ALTER TABLE student
ADD CONSTRAINT unique_email_students UNIQUE (email_address);

ALTER TABLE teacher
ADD CONSTRAINT unique_email_teachers UNIQUE (email);

ALTER TABLE faculty
ADD CONSTRAINT unique_email_faculty UNIQUE (email);

-- DEFAULT CONSTRAINT
ALTER TABLE payment
MODIFY amount INT DEFAULT 0;

-- Populate tables with data
INSERT INTO student (student_id, first_name, last_name, email_address, address, phone_no)
VALUES
    (1, 'Alice', 'Johnson', 'alice.johnson@example.com', '123 Main St', '1234567890'),
    (2, 'Bob', 'Smith', 'bob.smith@example.com', '456 Elm St', '0987654321'),
    (3, 'Carol', 'Davis', 'carol.davis@example.com', '789 Pine St', '5678901234'),
    (4, 'David', 'Wilson', 'david.wilson@example.com', '234 Oak St', '8901234567'),
    (5, 'Eve', 'Brown', 'eve.brown@example.com', '567 Cedar St', '1230984567'),
    (6, 'Frank', 'White', 'frank.white@example.com', '890 Birch St', '9876543210'),
    (7, 'Grace', 'Harris', 'grace.harris@example.com', '123 Spruce St', '3456789012'),
    (8, 'Hank', 'Martin', 'hank.martin@example.com', '456 Maple St', '5678901234'),
    (9, 'Ivy', 'Clark', 'ivy.clark@example.com', '789 Walnut St', '8901234567'),
    (10, 'Jack', 'Lewis', 'jack.lewis@example.com', '234 Cherry St', '1230987654'),
    (11, 'Kate', 'Young', 'kate.young@example.com', '567 Chestnut St', '3456789012'),
    (12, 'Leo', 'Allen', 'leo.allen@example.com', '890 Hickory St', '4567890123'),
    (13, 'Mona', 'Wright', 'mona.wright@example.com', '123 Dogwood St', '5678901234'),
    (14, 'Nina', 'Scott', 'nina.scott@example.com', '456 Sycamore St', '6789012345'),
    (15, 'Oscar', 'Adams', 'oscar.adams@example.com', '789 Beech St', '7890123456');

INSERT INTO faculty (faculty_id, faculty_name, email, phone_no)
VALUES
    (1, 'Faculty of Science', 'science_faculty@example.com', '1234567890'),
    (2, 'Faculty of Arts', 'arts_faculty@example.com', '0987654321');

INSERT INTO department (department_id, department_name, faculty_id)
VALUES
    (1, 'Computer Science', 1),
    (2, 'Mathematics', 1),
    (3, 'Physics', 1),
    (4, 'English', 2),
    (5, 'History', 2);
    
INSERT INTO courses (course_id, course_name, course_desc, credit_hours, prerequisite, department_id)
VALUES
    (1, 'Programming basics', 'Learn programming basics', 3, 'None', 1),
    (2, 'Data Structures', 'Learn about data structures', 3, 'Introduction to Programming', 1),
    (3, 'Linear Algebra', 'Study of linear equations', 3, 'None', 2),
    (4, 'Quantum Physics', 'Basics of quantum theory', 3, 'None', 3),
    (5, 'British Literature', 'Explore British literary works', 3, 'None', 4),
    (6, 'Modern History', 'Events from 19th century onwards', 3, 'None', 5),
    (7, 'Database Systems', 'Learn relational databases', 3, 'None', 1),
    (8, 'Advanced Mathematics', 'Higher-level mathematics topics', 3, 'Linear Algebra', 2),
    (9, 'Thermodynamics', 'Energy and heat flow', 3, 'None', 3),
    (10, 'American Literature', 'Explore American literary works', 3, 'None', 4);
    
INSERT INTO teacher (teacher_id, first_name, last_name, email, qualification, department_id)
VALUES
    (1, 'John', 'Doe', 'john.doe@example.com', 'PhD', 1),
    (2, 'Emily', 'Stone', 'emily.stone@example.com', 'MSc', 1),
    (3, 'Robert', 'Brown', 'robert.brown@example.com', 'PhD', 2),
    (4, 'Susan', 'Taylor', 'susan.taylor@example.com', 'PhD', 3),
    (5, 'Michael', 'Anderson', 'michael.anderson@example.com', 'PhD', 4),
    (6, 'Laura', 'Evans', 'laura.evans@example.com', 'PhD', 5),
    (7, 'James', 'Moore', 'james.moore@example.com', 'MSc', 1),
    (8, 'Anna', 'Green', 'anna.green@example.com', 'MSc', 2),
    (9, 'David', 'King', 'david.king@example.com', 'PhD', 3),
    (10, 'Sophia', 'Hill', 'sophia.hill@example.com', 'MSc', 4);

INSERT INTO payment (payment_id, payment_date, amount, payment_status, payment_method, student_id)
VALUES
    (1, '2024-01-15', 500, 'PAID', 'Credit Card', 1),
    (2, '2024-01-16', 500, 'PAID', 'Cash', 2),
    (3, '2024-01-17', 500, 'PAID', 'Bank Transfer', 3),
    (4, '2024-01-18', 500, 'PAID', 'Credit Card', 4),
    (5, '2024-01-19', 500, 'PAID', 'Cash', 5),
    (6, '2024-01-20', 500, 'PAID', 'Bank Transfer', 6),
    (7, '2024-01-21', 500, 'PAID', 'Credit Card', 7),
    (8, '2024-01-22', 500, 'PAID', 'Cash', 8),
    (9, '2024-01-23', 500, 'PAID', 'Bank Transfer', 9),
    (10, '2024-01-24', 500, 'PAID', 'Credit Card', 10),
    (11, '2024-01-25', 500, 'PAID', 'Cash', 11),
    (12, '2024-01-26', 500, 'PAID', 'Bank Transfer', 12),
    (13, '2024-01-27', 500, 'PAID', 'Credit Card', 13),
    (14, '2024-01-28', 500, 'PAID', 'Cash', 14),
    (15, '2024-01-29', 500, 'PAID', 'Bank Transfer', 15);
    
INSERT INTO enrollment (enrollment_id, enrollment_date, grade, enrollment_status, student_id, course_id)
VALUES
    (1, '2024-01-10', 'A', 'Active', 1, 1),
    (2, '2024-01-11', 'B', 'Active', 2, 2),
    (3, '2024-01-12', 'C', 'Active', 3, 3),
    (4, '2024-01-13', 'A', 'Active', 4, 4),
    (5, '2024-01-14', 'B', 'Active', 5, 5),
    (6, '2024-01-15', 'C', 'Active', 6, 6),
    (7, '2024-01-16', 'A', 'Active', 7, 7),
    (8, '2024-01-17', 'B', 'Active', 8, 8),
    (9, '2024-01-18', 'C', 'Active', 9, 9),
    (10, '2024-01-19', 'A', 'Active', 10, 10);

INSERT INTO exam (exam_id, exam_date, start_time, end_time, location, course_id)
VALUES
    (1, '2024-02-01', '10:00:00', '12:00:00', 'Room 101', 1),
    (2, '2024-02-02', '13:00:00', '15:00:00', 'Room 102', 2),
    (3, '2024-02-03', '10:00:00', '12:00:00', 'Room 103', 3),
    (4, '2024-02-04', '13:00:00', '15:00:00', 'Room 104', 4),
    (5, '2024-02-05', '10:00:00', '12:00:00', 'Room 105', 5),
    (6, '2024-02-06', '13:00:00', '15:00:00', 'Room 106', 6),
    (7, '2024-02-07', '10:00:00', '12:00:00', 'Room 107', 7),
    (8, '2024-02-08', '13:00:00', '15:00:00', 'Room 108', 8),
    (9, '2024-02-09', '10:00:00', '12:00:00', 'Room 109', 9),
    (10, '2024-02-10', '13:00:00', '15:00:00', 'Room 110', 10);

INSERT INTO classroom (classroom_id, room_no, capacity, building)
VALUES
    (1, 101, 50, 'Science Building'),
    (2, 102, 50, 'Science Building'),
    (3, 103, 40, 'Math Building'),
    (4, 104, 40, 'Math Building'),
    (5, 105, 60, 'Physics Building'),
    (6, 106, 60, 'Physics Building'),
    (7, 201, 50, 'Arts Building'),
    (8, 202, 50, 'Arts Building'),
    (9, 203, 45, 'History Building'),
    (10, 204, 45, 'History Building');

INSERT INTO class_schedule (schedule_id, class_day, start_time, end_time, course_id, classroom_id, teacher_id)
VALUES
    (1, 'Monday', '08:00:00', '10:00:00', 1, 1, 1),
    (2, 'Tuesday', '10:00:00', '12:00:00', 2, 2, 2),
    (3, 'Wednesday', '12:00:00', '14:00:00', 3, 3, 3),
    (4, 'Thursday', '14:00:00', '16:00:00', 4, 4, 4),
    (5, 'Friday', '08:00:00', '10:00:00', 5, 5, 5),
    (6, 'Monday', '10:00:00', '12:00:00', 6, 6, 6),
    (7, 'Tuesday', '12:00:00', '14:00:00', 7, 7, 7),
    (8, 'Wednesday', '14:00:00', '16:00:00', 8, 8, 8),
    (9, 'Thursday', '08:00:00', '10:00:00', 9, 9, 9),
    (10, 'Friday', '10:00:00', '12:00:00', 10, 10, 10);
    
    -- To get the data in the student table
    SELECT *
    FROM student;
    -- To get the data in the teacher table
    SELECT *
    FROM teacher;
    -- To get the data in the department table
    SELECT *
    FROM department;
    -- To get the data in the faculty table
    SELECT *
    FROM faculty;
    -- To get the data in the course table
    SELECT *
    FROM course;
    
-- Query to get students details
SELECT 
    student.first_name AS student_first_name, 
    student.last_name AS student_last_name, 
    department.department_name AS department_name,
    faculty.faculty_name AS faculty_name,
    payment.payment_method AS payment_method,
    courses.course_id AS course_id,
    courses.course_name AS course_name,
    enrollment.grade AS course_grade
FROM student
JOIN payment ON student.student_id = payment.student_id
JOIN enrollment ON student.student_id = enrollment.student_id
JOIN courses ON enrollment.course_id = courses.course_id
JOIN department ON courses.department_id = department.department_id
JOIN faculty ON department.faculty_id = faculty.faculty_id;

-- USING PARAMETERIZED QUERY TO RETRIEVE SENSITIVE DATA
PREPARE stmt FROM 
'SELECT 
    student.first_name, 
    student.last_name, 
    courses.course_name, 
    enrollment.grade
 FROM student
 JOIN enrollment ON student.student_id = enrollment.student_id
 JOIN courses ON enrollment.course_id = courses.course_id
 WHERE student.student_id = ?';
 
SET @student_id = 1;

EXECUTE stmt USING @student_id;


DEALLOCATE PREPARE stmt;



