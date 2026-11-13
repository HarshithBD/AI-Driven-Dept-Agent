-- ==============================================================================
-- AIDA – AI-Driven Department Agent
-- Complete Master Schema & Seed Data for Supabase PostgreSQL
-- ==============================================================================
-- Instructions:
-- 1. Open your Supabase Dashboard: https://supabase.com/dashboard/project/xiwiftiscfsyuuavhmdc
-- 2. Click "SQL Editor" in the left sidebar
-- 3. Click "New Query", paste this entire script, and click "Run"
-- ==============================================================================

-- Enable UUID extension if not enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ==============================================================================
-- 1. USER ROLES (RBAC: student, faculty, admin)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.user_roles (
    id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('student', 'faculty', 'admin'))
);
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow public read access to user_roles') THEN
        CREATE POLICY "Allow public read access to user_roles" 
        ON public.user_roles FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role full access to user_roles') THEN
        CREATE POLICY "Allow service role full access to user_roles" 
        ON public.user_roles USING (true) WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow user to insert own role') THEN
        CREATE POLICY "Allow user to insert own role" 
        ON public.user_roles FOR INSERT WITH CHECK (auth.uid() = id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow user to update own role') THEN
        CREATE POLICY "Allow user to update own role" 
        ON public.user_roles FOR UPDATE USING (auth.uid() = id);
    END IF;
END $$;

-- ==============================================================================
-- 2. CHAT SESSIONS (User Conversation History)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    title TEXT NOT NULL,
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON public.chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated_at ON public.chat_sessions(updated_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow users to select their own sessions') THEN
        CREATE POLICY "Allow users to select their own sessions" 
        ON public.chat_sessions FOR SELECT USING (auth.uid() = user_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow users to insert their own sessions') THEN
        CREATE POLICY "Allow users to insert their own sessions" 
        ON public.chat_sessions FOR INSERT WITH CHECK (auth.uid() = user_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow users to update their own sessions') THEN
        CREATE POLICY "Allow users to update their own sessions" 
        ON public.chat_sessions FOR UPDATE USING (auth.uid() = user_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow users to delete their own sessions') THEN
        CREATE POLICY "Allow users to delete their own sessions" 
        ON public.chat_sessions FOR DELETE USING (auth.uid() = user_id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow public service access to chat_sessions') THEN
        CREATE POLICY "Allow public service access to chat_sessions" 
        ON public.chat_sessions USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 3. CHAT LOGS (Telemetry & Monitoring)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.chat_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    query TEXT NOT NULL,
    intent TEXT NOT NULL,
    latency_ms INTEGER NOT NULL
);
ALTER TABLE public.chat_logs ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS idx_chat_logs_created_at ON public.chat_logs(created_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow public read access to chat_logs') THEN
        CREATE POLICY "Allow public read access to chat_logs" 
        ON public.chat_logs FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow public insert access to chat_logs') THEN
        CREATE POLICY "Allow public insert access to chat_logs" 
        ON public.chat_logs FOR INSERT WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 4. FACULTY DIRECTORY
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.faculty (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    designation TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'AIML',
    email TEXT UNIQUE NOT NULL,
    contact_info TEXT,
    specialization TEXT,
    subjects_handled TEXT[] DEFAULT '{}',
    availability TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.faculty ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_faculty_dept ON public.faculty(department);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read faculty') THEN
        CREATE POLICY "Allow read faculty" ON public.faculty FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role write faculty') THEN
        CREATE POLICY "Allow service role write faculty" ON public.faculty FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 5. STUDENTS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.students (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    enrollment_no TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    department TEXT NOT NULL DEFAULT 'AIML',
    semester INTEGER NOT NULL DEFAULT 6,
    section TEXT NOT NULL DEFAULT 'AIML-A',
    batch_year TEXT DEFAULT '2023-2027',
    contact_number TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_students_dept_sec ON public.students(department, section);
CREATE INDEX IF NOT EXISTS idx_students_user_id ON public.students(user_id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read students') THEN
        CREATE POLICY "Allow read students" ON public.students FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role write students') THEN
        CREATE POLICY "Allow service role write students" ON public.students FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 6. SUBJECTS (Course Catalog)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.subjects (
    id VARCHAR(16) PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'AIML',
    semester INTEGER NOT NULL DEFAULT 6,
    credits INTEGER NOT NULL DEFAULT 3,
    description TEXT,
    syllabus_url TEXT,
    faculty_in_charge_id UUID REFERENCES public.faculty(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.subjects ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_subjects_dept ON public.subjects(department);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read subjects') THEN
        CREATE POLICY "Allow read subjects" ON public.subjects FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role write subjects') THEN
        CREATE POLICY "Allow service role write subjects" ON public.subjects FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 7. TIMETABLE
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.timetable (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    day TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    subject_id VARCHAR(16) REFERENCES public.subjects(id) ON DELETE SET NULL,
    subject_name TEXT NOT NULL,
    faculty_id UUID REFERENCES public.faculty(id) ON DELETE SET NULL,
    faculty_name TEXT,
    room TEXT NOT NULL,
    student_group TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'AIML',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.timetable ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_timetable_day_group ON public.timetable(day, student_group);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read timetable') THEN
        CREATE POLICY "Allow read timetable" ON public.timetable FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role write timetable') THEN
        CREATE POLICY "Allow service role write timetable" ON public.timetable FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 8. NOTICES
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.notices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'AIML',
    category TEXT NOT NULL DEFAULT 'Academic',
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    is_pinned BOOLEAN NOT NULL DEFAULT false,
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.notices ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_notices_dept_date ON public.notices(department, date DESC);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read notices') THEN
        CREATE POLICY "Allow read notices" ON public.notices FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role write notices') THEN
        CREATE POLICY "Allow service role write notices" ON public.notices FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 9. EVENTS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    date_time TIMESTAMPTZ NOT NULL,
    location TEXT NOT NULL,
    organizer TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'AIML',
    created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_events_datetime ON public.events(date_time ASC);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read events') THEN
        CREATE POLICY "Allow read events" ON public.events FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role write events') THEN
        CREATE POLICY "Allow service role write events" ON public.events FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 10. ACADEMIC DOCUMENTS
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.academic_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    category TEXT NOT NULL,
    department TEXT NOT NULL DEFAULT 'AIML',
    year TEXT,
    course TEXT,
    file_size_bytes BIGINT,
    uploaded_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.academic_documents ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read academic_documents') THEN
        CREATE POLICY "Allow read academic_documents" ON public.academic_documents FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role write academic_documents') THEN
        CREATE POLICY "Allow service role write academic_documents" ON public.academic_documents FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 11. STUDENT REQUESTS (Approval Workflow)
-- ==============================================================================
CREATE TABLE IF NOT EXISTS public.student_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID REFERENCES public.students(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    request_type TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Under Review', 'In Review', 'Approved', 'Rejected', 'More Information Required')),
    assigned_to UUID REFERENCES public.faculty(id) ON DELETE SET NULL,
    comments TEXT,
    history JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.student_requests ENABLE ROW LEVEL SECURITY;
CREATE INDEX IF NOT EXISTS idx_student_requests_status ON public.student_requests(status);
CREATE INDEX IF NOT EXISTS idx_student_requests_user ON public.student_requests(user_id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow select student_requests') THEN
        CREATE POLICY "Allow select student_requests" ON public.student_requests FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow insert student_requests') THEN
        CREATE POLICY "Allow insert student_requests" ON public.student_requests FOR INSERT WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow update student_requests') THEN
        CREATE POLICY "Allow update student_requests" ON public.student_requests FOR UPDATE USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow service role write student_requests') THEN
        CREATE POLICY "Allow service role write student_requests" ON public.student_requests FOR ALL USING (true) WITH CHECK (true);
    END IF;
END $$;

-- ==============================================================================
-- 12. AUTOMATIC UPDATED_AT TRIGGER FUNCTION
-- ==============================================================================
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_faculty_updated_at ON public.faculty;
CREATE TRIGGER trg_faculty_updated_at BEFORE UPDATE ON public.faculty FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS trg_students_updated_at ON public.students;
CREATE TRIGGER trg_students_updated_at BEFORE UPDATE ON public.students FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS trg_events_updated_at ON public.events;
CREATE TRIGGER trg_events_updated_at BEFORE UPDATE ON public.events FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS trg_student_requests_updated_at ON public.student_requests;
CREATE TRIGGER trg_student_requests_updated_at BEFORE UPDATE ON public.student_requests FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

DROP TRIGGER IF EXISTS trg_chat_sessions_updated_at ON public.chat_sessions;
CREATE TRIGGER trg_chat_sessions_updated_at BEFORE UPDATE ON public.chat_sessions FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- ==============================================================================
-- 13. SEED DATA (AIML DEPARTMENT)
-- ==============================================================================

-- Subjects
INSERT INTO public.subjects (id, name, department, semester, credits, description)
VALUES
    ('AI401', 'Machine Learning Foundations', 'AIML', 6, 4, 'Supervised and unsupervised learning, decision trees, regression, and model evaluation.'),
    ('AI402', 'Deep Learning & Neural Networks', 'AIML', 6, 4, 'CNNs, RNNs, Transformers, attention mechanisms, backpropagation, and PyTorch implementations.'),
    ('AI403', 'Natural Language Processing', 'AIML', 6, 3, 'Text processing, word embeddings, sequence-to-sequence models, and Large Language Models.'),
    ('AI404', 'Computer Vision', 'AIML', 6, 3, 'Image filtering, feature extraction, object detection (YOLO), segmentation, and 3D perception.'),
    ('AI405', 'Reinforcement Learning & Robotics', 'AIML', 6, 3, 'Markov Decision Processes, Q-learning, policy gradients, trajectory planning, and robot simulation.'),
    ('AI406', 'AI Ethics & Governance', 'AIML', 6, 2, 'Fairness, accountability, transparency, data privacy regulations, and responsible AI deployment.')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    credits = EXCLUDED.credits,
    description = EXCLUDED.description;

-- Faculty
INSERT INTO public.faculty (name, designation, department, email, contact_info, specialization, subjects_handled, availability)
VALUES
    ('Dr. A. Sharma', 'Professor & Head of Department', 'AIML', 'hod.aiml@greenfield.edu', 'Cabin 401, AIML Block • Ext 4101', 'Machine Learning, Deep Learning, Predictive Modeling', ARRAY['AI401', 'AI402'], 'Mon & Wed: 2:00 PM - 4:00 PM'),
    ('Prof. K. Patel', 'Associate Professor', 'AIML', 'k.patel@greenfield.edu', 'Cabin 402, AIML Block • Ext 4102', 'Neural Architectures, GPU Computing, Optimization', ARRAY['AI402'], 'Tue & Thu: 11:00 AM - 1:00 PM'),
    ('Dr. R. Verma', 'Assistant Professor', 'AIML', 'r.verma@greenfield.edu', 'Cabin 403, AIML Block • Ext 4103', 'Natural Language Processing, LLMs, Conversational AI', ARRAY['AI403'], 'Daily: 3:00 PM - 4:30 PM'),
    ('Prof. S. Rao', 'Assistant Professor', 'AIML', 's.rao@greenfield.edu', 'Cabin 404, AIML Block • Ext 4104', 'Computer Vision, Edge AI, Autonomous Systems', ARRAY['AI404'], 'Mon & Fri: 10:00 AM - 12:00 PM'),
    ('Dr. M. Gupta', 'Assistant Professor', 'AIML', 'm.gupta@greenfield.edu', 'Cabin 405, AIML Block • Ext 4105', 'Reinforcement Learning, Robotics, Control Theory', ARRAY['AI405'], 'Wed & Thu: 2:00 PM - 3:30 PM'),
    ('Prof. N. Iyer', 'Visiting Professor', 'AIML', 'n.iyer@greenfield.edu', 'Cabin 406, AIML Block • Ext 4106', 'AI Ethics, Governance, Responsible AI, Data Policy', ARRAY['AI406'], 'Friday: 2:00 PM - 5:00 PM')
ON CONFLICT (email) DO UPDATE SET
    contact_info = EXCLUDED.contact_info,
    availability = EXCLUDED.availability,
    subjects_handled = EXCLUDED.subjects_handled;

-- Sample Students
INSERT INTO public.students (enrollment_no, full_name, email, department, semester, section, batch_year, contact_number)
VALUES
    ('EN2023AIML001', 'Aarav Patel', 'aarav.patel@student.greenfield.edu', 'AIML', 6, 'AIML-A', '2023-2027', '+91 98765 43210'),
    ('EN2023AIML002', 'Diya Sharma', 'diya.sharma@student.greenfield.edu', 'AIML', 6, 'AIML-A', '2023-2027', '+91 98765 43211'),
    ('EN2023AIML051', 'Rohan Deshmukh', 'rohan.deshmukh@student.greenfield.edu', 'AIML', 6, 'AIML-B', '2023-2027', '+91 98765 43212'),
    ('EN2023AIML052', 'Ananya Iyer', 'ananya.iyer@student.greenfield.edu', 'AIML', 6, 'AIML-B', '2023-2027', '+91 98765 43213')
ON CONFLICT (enrollment_no) DO NOTHING;

-- Events
INSERT INTO public.events (title, description, date_time, location, organizer, department)
VALUES
    ('Annual AIML Hackathon 2026', 'Inter-department 36-hour hackathon focused on Generative AI and Autonomous Agent Systems.', now() + interval '14 days', 'AIML Computing Labs 401-403', 'AIML Student Chapter', 'AIML'),
    ('Distinguished Industry Talk: Foundation Models in Production', 'Interactive session with leading AI research engineers on scaling multimodal vision-language models.', now() + interval '6 days', 'Seminar Hall 2, Academic Complex', 'Dept Industry Relations Cell', 'AIML'),
    ('Hands-on Workshop: Edge AI with NVIDIA Jetson', 'Hands-on practical training on deploying quantized computer vision models onto edge robotics hardware.', now() + interval '20 days', 'Robotics & Vision Lab (Lab 402)', 'AIML Robotics Club', 'AIML')
ON CONFLICT DO NOTHING;

-- Notices
INSERT INTO public.notices (title, content, department, category, date, is_pinned)
VALUES
    ('AIML Annual AI Hackathon 2026 Registration Open', 'Registration is open for the AIML Department Annual Hackathon: Generative AI and Autonomous Systems. Inter-department teams permitted. Prize pool and GPU compute credits provided.', 'AIML', 'Event', CURRENT_DATE, true),
    ('AIML Semester Exams & Lab Assessment Schedule', 'Mid-semester theory examinations and laboratory practical evaluations for AIML batches (AIML-A and AIML-B) will commence on April 18th. Detailed seating plans posted on notice board.', 'AIML', 'Examination', CURRENT_DATE, true),
    ('High Performance AI Lab Server Maintenance', 'GPU cluster in Lab 401 (AIML Block) will undergo scheduled hypervisor and driver upgrades on Saturday from 10 AM to 4 PM. Save training checkpoints before maintenance window.', 'AIML', 'Facility', CURRENT_DATE, false),
    ('Guest Lecture on Multimodal Foundation Models', 'Distinguished Industry Speaker session on "Scaling Multimodal Vision-Language Models in Production" on Wednesday at 2:30 PM in Seminar Hall 2.', 'AIML', 'Academic', CURRENT_DATE, false),
    ('Hostel & Campus Facilities Maintenance', 'Block A and Student Center will undergo water pipeline maintenance from 10 AM to 3 PM on March 28th.', 'General', 'Facility', CURRENT_DATE, false)
ON CONFLICT DO NOTHING;

-- Timetable (AIML-A and AIML-B)
INSERT INTO public.timetable (day, time_slot, subject_id, subject_name, faculty_name, room, student_group, department)
VALUES
    -- Monday AIML-A
    ('Monday', '08:00-09:00', 'AI401', 'Machine Learning Foundations', 'Dr. A. Sharma', 'Room 401', 'AIML-A', 'AIML'),
    ('Monday', '09:00-10:00', 'AI402', 'Deep Learning & Neural Networks', 'Prof. K. Patel', 'Lab 401', 'AIML-A', 'AIML'),
    ('Monday', '10:00-11:00', 'AI403', 'Natural Language Processing', 'Dr. R. Verma', 'Room 401', 'AIML-A', 'AIML'),
    ('Monday', '11:00-12:00', 'AI404', 'Computer Vision', 'Prof. S. Rao', 'Lab 402', 'AIML-A', 'AIML'),
    -- Monday AIML-B
    ('Monday', '08:00-09:00', 'AI402', 'Deep Learning & Neural Networks', 'Prof. K. Patel', 'Lab 401', 'AIML-B', 'AIML'),
    ('Monday', '09:00-10:00', 'AI401', 'Machine Learning Foundations', 'Dr. A. Sharma', 'Room 402', 'AIML-B', 'AIML'),
    ('Monday', '10:00-11:00', 'AI405', 'Reinforcement Learning & Robotics', 'Dr. M. Gupta', 'Room 402', 'AIML-B', 'AIML'),
    ('Monday', '11:00-12:00', 'AI403', 'Natural Language Processing', 'Dr. R. Verma', 'Lab 403', 'AIML-B', 'AIML'),
    -- Tuesday AIML-A
    ('Tuesday', '08:00-09:00', 'AI405', 'Reinforcement Learning & Robotics', 'Dr. M. Gupta', 'Room 401', 'AIML-A', 'AIML'),
    ('Tuesday', '09:00-10:00', 'AI401', 'Machine Learning Foundations', 'Dr. A. Sharma', 'Lab 401', 'AIML-A', 'AIML'),
    ('Tuesday', '10:00-11:00', 'AI406', 'AI Ethics & Governance', 'Prof. N. Iyer', 'Room 401', 'AIML-A', 'AIML'),
    ('Tuesday', '11:00-12:00', 'AI402', 'Deep Learning & Neural Networks', 'Prof. K. Patel', 'Room 401', 'AIML-A', 'AIML'),
    -- Tuesday AIML-B
    ('Tuesday', '08:00-09:00', 'AI406', 'AI Ethics & Governance', 'Prof. N. Iyer', 'Room 402', 'AIML-B', 'AIML'),
    ('Tuesday', '09:00-10:00', 'AI405', 'Reinforcement Learning & Robotics', 'Dr. M. Gupta', 'Lab 402', 'AIML-B', 'AIML'),
    ('Tuesday', '10:00-11:00', 'AI401', 'Machine Learning Foundations', 'Dr. A. Sharma', 'Room 402', 'AIML-B', 'AIML'),
    ('Tuesday', '11:00-12:00', 'AI404', 'Computer Vision', 'Prof. S. Rao', 'Room 402', 'AIML-B', 'AIML'),
    -- Wednesday AIML-A
    ('Wednesday', '08:00-09:00', 'AI403', 'Natural Language Processing', 'Dr. R. Verma', 'Room 401', 'AIML-A', 'AIML'),
    ('Wednesday', '09:00-10:00', 'AI405', 'Reinforcement Learning & Robotics', 'Dr. M. Gupta', 'Lab 402', 'AIML-A', 'AIML'),
    ('Wednesday', '10:00-11:00', 'AI401', 'Machine Learning Foundations', 'Dr. A. Sharma', 'Room 401', 'AIML-A', 'AIML'),
    ('Wednesday', '11:00-12:00', 'AI404', 'Computer Vision', 'Prof. S. Rao', 'Room 401', 'AIML-A', 'AIML'),
    -- Wednesday AIML-B
    ('Wednesday', '08:00-09:00', 'AI402', 'Deep Learning & Neural Networks', 'Prof. K. Patel', 'Room 402', 'AIML-B', 'AIML'),
    ('Wednesday', '09:00-10:00', 'AI403', 'Natural Language Processing', 'Dr. R. Verma', 'Lab 403', 'AIML-B', 'AIML'),
    ('Wednesday', '10:00-11:00', 'AI404', 'Computer Vision', 'Prof. S. Rao', 'Room 402', 'AIML-B', 'AIML'),
    ('Wednesday', '11:00-12:00', 'AI405', 'Reinforcement Learning & Robotics', 'Dr. M. Gupta', 'Room 402', 'AIML-B', 'AIML'),
    -- Thursday AIML-A
    ('Thursday', '08:00-09:00', 'AI402', 'Deep Learning & Neural Networks', 'Prof. K. Patel', 'Room 401', 'AIML-A', 'AIML'),
    ('Thursday', '09:00-10:00', 'AI404', 'Computer Vision', 'Prof. S. Rao', 'Lab 402', 'AIML-A', 'AIML'),
    ('Thursday', '10:00-11:00', 'AI405', 'Reinforcement Learning & Robotics', 'Dr. M. Gupta', 'Lab 401', 'AIML-A', 'AIML'),
    ('Thursday', '11:00-12:00', 'AI403', 'Natural Language Processing', 'Dr. R. Verma', 'Room 401', 'AIML-A', 'AIML'),
    -- Thursday AIML-B
    ('Thursday', '08:00-09:00', 'AI403', 'Natural Language Processing', 'Dr. R. Verma', 'Room 402', 'AIML-B', 'AIML'),
    ('Thursday', '09:00-10:00', 'AI402', 'Deep Learning & Neural Networks', 'Prof. K. Patel', 'Room 402', 'AIML-B', 'AIML'),
    ('Thursday', '10:00-11:00', 'AI406', 'AI Ethics & Governance', 'Prof. N. Iyer', 'Room 402', 'AIML-B', 'AIML'),
    ('Thursday', '11:00-12:00', 'AI401', 'Machine Learning Foundations', 'Dr. A. Sharma', 'Lab 401', 'AIML-B', 'AIML'),
    -- Friday AIML-A
    ('Friday', '08:00-09:00', 'AI401', 'Machine Learning Foundations', 'Dr. A. Sharma', 'Room 401', 'AIML-A', 'AIML'),
    ('Friday', '09:00-10:00', 'AI403', 'Natural Language Processing', 'Dr. R. Verma', 'Lab 403', 'AIML-A', 'AIML'),
    ('Friday', '10:00-11:00', 'AI402', 'Deep Learning & Neural Networks', 'Prof. K. Patel', 'Lab 401', 'AIML-A', 'AIML'),
    ('Friday', '11:00-12:00', 'AI406', 'AI Ethics & Governance', 'Prof. N. Iyer', 'Room 401', 'AIML-A', 'AIML'),
    -- Friday AIML-B
    ('Friday', '08:00-09:00', 'AI405', 'Reinforcement Learning & Robotics', 'Dr. M. Gupta', 'Room 402', 'AIML-B', 'AIML'),
    ('Friday', '09:00-10:00', 'AI404', 'Computer Vision', 'Prof. S. Rao', 'Lab 402', 'AIML-B', 'AIML'),
    ('Friday', '10:00-11:00', 'AI403', 'Natural Language Processing', 'Dr. R. Verma', 'Room 402', 'AIML-B', 'AIML'),
    ('Friday', '11:00-12:00', 'AI402', 'Deep Learning & Neural Networks', 'Prof. K. Patel', 'Room 402', 'AIML-B', 'AIML')
ON CONFLICT DO NOTHING;

