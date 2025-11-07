-- Insert Countries
INSERT INTO COUNTRIES (code, name) VALUES
(1, 'Colombia');

-- Insert Departments
INSERT INTO DEPARTMENTS (code, name, country_code) VALUES
(1, 'Valle del Cauca', 1),
(2, 'Cundinamarca', 1),
(5, 'Antioquia', 1),
(8, 'Atlántico', 1),
(11, 'Bogotá D.C.', 1);



-- Insert Cities
INSERT INTO CITIES (code, name, dept_code) VALUES
(101, 'Cali', 1),
(102, 'Bogotá', 11),
(103, 'Medellín', 5),
(104, 'Barranquilla', 8),
(105, 'Soledad', 8);

-- Insert Faculties
INSERT INTO FACULTIES (code, name, location, phone_number, dean_id) VALUES
(1, 'Facultad de Ciencias', 'Call3', '555-1234', '1001'),
(2, 'Facultad de Ingeniería', 'Call4', '555-5678', '1002');

-- Insert Campuses
INSERT INTO CAMPUSES (code, name, city_code) VALUES
(1, 'Campus Cali', 101),
(2, 'Campus Bogotá', 102),
(3, 'Campus Medellín', 103),
(4, 'Campus Barranquilla', 104);

-- Insert Employee Types
INSERT INTO EMPLOYEE_TYPES (name) VALUES
('Docente'),
('Administrativo'), ('Instructor');

-- Insert Contract Types
INSERT INTO CONTRACT_TYPES (name) VALUES
('Planta'),
('Cátedra');

-- Insert Employees
INSERT INTO EMPLOYEES (id, first_name, last_name, email, contract_type, employee_type, faculty_code, campus_code, birth_place_code) VALUES
('1001', 'Juan', 'Pérez', 'juan.perez@univcali.edu.co', 'Planta', 'Docente', 1, 1, 101),
('1002', 'María', 'Gómez', 'maria.gomez@univcali.edu.co', 'Planta', 'Administrativo', 1, 2, 102),
('1003', 'Carlos', 'López', 'carlos.lopez@univcali.edu.co', 'Cátedra', 'Docente', 2, 1, 103),
('1004', 'Carlos', 'Mejía', 'carlos.mejia@univcali.edu.co', 'Planta', 'Docente', 1, 3, 103),
('1005', 'Sandra', 'Ortiz', 'sandra.ortiz@univcali.edu.co', 'Cátedra', 'Docente', 2, 4, 104),
('1006', 'Julián', 'Reyes', 'julian.reyes@univcali.edu.co', 'Planta', 'Administrativo', 2, 1, 105),
('1007', 'Paula', 'Ramírez', 'paula.ramirez@univcali.edu.co', 'Planta', 'Instructor', 1,1, 101),
('1008', 'Andrés', 'Castro', 'andres.castro@univcali.edu.co', 'Cátedra', 'Instructor', 1, 3,103);

-- Insert Areas
INSERT INTO AREAS (code, name, faculty_code, coordinator_id) VALUES
(1, 'Área de Sociales', 1, '1001'),
(2, 'Área de Ingeniería', 2, '1003'),
(3, 'Área de Bienestar', 1, '1007');

-- Insert Programs
INSERT INTO PROGRAMS (code, name, area_code) VALUES
(1, 'Psicología', 1),
(2, 'Ingeniería de Sistemas', 2);

-- Insert Subjects
INSERT INTO SUBJECTS (code, name, program_code) VALUES
('S101', 'Psicología General', 1),
('S102', 'Cálculo I', 2),
('S103', 'Programación', 2),
('S104', 'Estructuras de Datos', 2),
('S105', 'Bases de Datos', 2),
('S106', 'Redes de Computadores', 2),
('S107', 'Sistemas Operativos', 2),
('S108', 'Algoritmos Avanzados', 2);


-- Insert Groups (con NRC como PK)
INSERT INTO GROUPS (NRC, number, semester, subject_code, professor_id) VALUES
('G101', 1, '2023-2', 'S101', '1001'),
('G102', 2, '2023-2', 'S102', '1003'),
('G103', 3, '2023-2', 'S103', '1004'),
('G104', 4, '2023-2', 'S105', '1005'),
('G105', 5, '2023-2', 'S106', '1004');

-- Insert Students
INSERT INTO STUDENTS (id, first_name, last_name, email, birth_date, birth_place_code, campus_code) VALUES
('2001', 'Laura', 'Hernández', 'laura.hernandez@univcali.edu.co', '2000-03-15', 101, 1),
('2002', 'Pedro', 'Martínez', 'pedro.martinez@univcali.edu.co', '1999-07-22', 103, 1),
('2003', 'Ana', 'Suárez', 'ana.suarez@univcali.edu.co', '2001-01-05', 102, 2),
('2004', 'Luis', 'Ramírez', 'luis.ramirez@univcali.edu.co', '1998-11-30', 104, 3),
('2005', 'Sofía', 'García', 'sofia.garcia@univcali.edu.co', '2000-09-12', 105, 2);


-- Insert Enrollments (con FK a STUDENTS y GROUPS)
INSERT INTO ENROLLMENTS (student_id, NRC, enrollment_date, status) VALUES
('2001', 'G101', '2023-08-01', 'Active'),
('2001', 'G102', '2023-08-01', 'Active'),
('2002', 'G103', '2023-08-02', 'Active'),
('2003', 'G103', '2023-08-02', 'Active'),
('2004', 'G104', '2023-08-03', 'Withdrawn'),
('2005', 'G105', '2023-08-03', 'Active');

-- Insert Users
INSERT INTO USERS (username, password_hash, role, student_id, employee_id, is_active, created_at) VALUES
-- Estudiantes
('laura.h', 'hash_lh123', 'STUDENT', '2001', NULL, TRUE, CURRENT_TIMESTAMP),
('pedro.m', 'hash_pm123', 'STUDENT', '2002', NULL, TRUE, CURRENT_TIMESTAMP),
('ana.s', 'hash_as123', 'STUDENT', '2003', NULL, TRUE, CURRENT_TIMESTAMP),
('luis.r', 'hash_lr123', 'STUDENT', '2004', NULL, TRUE, CURRENT_TIMESTAMP),
('sofia.g', 'hash_sg123', 'STUDENT', '2005', NULL, TRUE, CURRENT_TIMESTAMP),

-- Empleados (profesores y administrativos)
('juan.p', 'hash_jp123', 'EMPLOYEE', NULL, '1001', TRUE, CURRENT_TIMESTAMP),
('maria.g', 'hash_mg123', 'EMPLOYEE', NULL, '1002', TRUE, CURRENT_TIMESTAMP),
('carlos.l', 'hash_cl123', 'EMPLOYEE', NULL, '1003', TRUE, CURRENT_TIMESTAMP),
('carlos.m', 'hash_cm123', 'EMPLOYEE', NULL, '1004', TRUE, CURRENT_TIMESTAMP),
('sandra.o', 'hash_so123', 'EMPLOYEE', NULL, '1005', TRUE, CURRENT_TIMESTAMP),
('paula.r', 'hash_pr123', 'EMPLOYEE', NULL, '1007', TRUE, CURRENT_TIMESTAMP),
('andres.c', 'hash_ac123', 'EMPLOYEE', NULL, '1008', TRUE, CURRENT_TIMESTAMP);




-- Insert Foreign Key Constraints
ALTER TABLE STUDENTS ADD CONSTRAINT STUDENTS_CITIES_FK 
    FOREIGN KEY (birth_place_code) REFERENCES CITIES (code);

ALTER TABLE STUDENTS ADD CONSTRAINT STUDENTS_CAMPUSES_FK 
    FOREIGN KEY (campus_code) REFERENCES CAMPUSES (code);
	

ALTER TABLE AREAS ADD CONSTRAINT AREAS_EMPLOYEES_FK FOREIGN KEY (coordinator_id) REFERENCES EMPLOYEES (id);
ALTER TABLE AREAS ADD CONSTRAINT AREAS_FACULTIES_FK FOREIGN KEY (faculty_code) REFERENCES FACULTIES (code);

ALTER TABLE SUBJECTS ADD CONSTRAINT SUBJECTS_PROGRAMS_FK FOREIGN KEY (program_code) REFERENCES PROGRAMS (code);

ALTER TABLE CITIES ADD CONSTRAINT CITIES_DEPARTMENTS_FK FOREIGN KEY (dept_code) REFERENCES DEPARTMENTS (code);

ALTER TABLE DEPARTMENTS ADD CONSTRAINT DEPARTMENTS_COUNTRIES_FK FOREIGN KEY (country_code) REFERENCES COUNTRIES (code);

ALTER TABLE EMPLOYEES ADD CONSTRAINT EMPLOYEES_CONTRACT_TYPES_FK FOREIGN KEY (contract_type) REFERENCES CONTRACT_TYPES (name);
ALTER TABLE EMPLOYEES ADD CONSTRAINT EMPLOYEES_CITIES_FK FOREIGN KEY (birth_place_code) REFERENCES CITIES (code);
ALTER TABLE EMPLOYEES ADD CONSTRAINT EMPLOYEES_FACULTIES_FK FOREIGN KEY (faculty_code) REFERENCES FACULTIES (code);
ALTER TABLE EMPLOYEES ADD CONSTRAINT EMPLOYEES_CAMPUSES_FK FOREIGN KEY (campus_code) REFERENCES CAMPUSES (code);
ALTER TABLE EMPLOYEES ADD CONSTRAINT EMPLOYEES_EMPLOYEE_TYPES_FK FOREIGN KEY (employee_type) REFERENCES EMPLOYEE_TYPES (name);

ALTER TABLE FACULTIES ADD CONSTRAINT FACULTIES_EMPLOYEES_FK FOREIGN KEY (dean_id) REFERENCES EMPLOYEES (id);

ALTER TABLE GROUPS ADD CONSTRAINT GROUPS_SUBJECTS_FK FOREIGN KEY (subject_code) REFERENCES SUBJECTS (code);
ALTER TABLE GROUPS ADD CONSTRAINT GROUPS_EMPLOYEES_FK FOREIGN KEY (professor_id) REFERENCES EMPLOYEES (id);

ALTER TABLE PROGRAMS ADD CONSTRAINT PROGRAMS_AREAS_FK FOREIGN KEY (area_code) REFERENCES AREAS (code);

ALTER TABLE CAMPUSES ADD CONSTRAINT CAMPUSES_CITIES_FK FOREIGN KEY (city_code) REFERENCES CITIES (code);



ALTER TABLE ENROLLMENTS ADD CONSTRAINT ENROLLMENTS_PK 
    PRIMARY KEY (student_id, NRC);

ALTER TABLE ENROLLMENTS ADD CONSTRAINT ENROLLMENTS_STUDENTS_FK 
    FOREIGN KEY (student_id) REFERENCES STUDENTS (id);

ALTER TABLE ENROLLMENTS ADD CONSTRAINT ENROLLMENTS_GROUPS_FK 
    FOREIGN KEY (NRC) 
    REFERENCES GROUPS (NRC);
	
