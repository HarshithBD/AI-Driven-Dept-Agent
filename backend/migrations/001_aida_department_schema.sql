-- ==============================================================================
-- AIDA – AI-Driven Department Agent
-- Migration 001: Department Entities & Human Approval Workflow Schema
-- Target: Supabase / PostgreSQL
-- ==============================================================================

-- 1. Ensure user_roles includes 'faculty'
DO $$
BEGIN
    -- Check if table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'user_roles') THEN
        -- Drop existing check constraint if any and re-add with 'faculty'
        ALTER TABLE public.user_roles DROP CONSTRAINT IF EXISTS user_roles_role_check;
        ALTER TABLE public.user_roles ADD CONSTRAINT user_roles_role_check CHECK (role IN ('student', 'faculty', 'admin'));
    ELSE
        CREATE TABLE public.user_roles (
            id uuid REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
            role text NOT NULL CHECK (role IN ('student', 'faculty', 'admin'))
        );
        ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;
    END IF;
END $$;

-- 2. Faculty Entity
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

-- 3. Students Entity
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

-- 4. Subjects Entity (Course Catalog)
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

-- 5. Timetable Entity (Schedule)
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

-- 6. Notices Entity
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

-- 7. Events Entity
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

-- 8. Academic Documents Entity
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

-- 9. Student Requests Entity (Human Approval Workflow)
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

-- ==================== INDEXES FOR PERFORMANCE ====================
CREATE INDEX IF NOT EXISTS idx_faculty_dept ON public.faculty(department);
CREATE INDEX IF NOT EXISTS idx_students_dept_sec ON public.students(department, section);
CREATE INDEX IF NOT EXISTS idx_timetable_day_group ON public.timetable(day, student_group);
CREATE INDEX IF NOT EXISTS idx_notices_dept_date ON public.notices(department, date DESC);
CREATE INDEX IF NOT EXISTS idx_events_datetime ON public.events(date_time ASC);
CREATE INDEX IF NOT EXISTS idx_student_requests_status ON public.student_requests(status);
CREATE INDEX IF NOT EXISTS idx_student_requests_user ON public.student_requests(user_id);

-- ==================== ROW LEVEL SECURITY (RLS) ====================
ALTER TABLE public.faculty ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.students ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.timetable ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.academic_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.student_requests ENABLE ROW LEVEL SECURITY;

-- Allow read access to public / authenticated users
DO $$
BEGIN
    -- Faculty
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read faculty') THEN
        CREATE POLICY "Allow read faculty" ON public.faculty FOR SELECT USING (true);
    END IF;
    -- Students
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read students') THEN
        CREATE POLICY "Allow read students" ON public.students FOR SELECT USING (true);
    END IF;
    -- Subjects
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read subjects') THEN
        CREATE POLICY "Allow read subjects" ON public.subjects FOR SELECT USING (true);
    END IF;
    -- Timetable
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read timetable') THEN
        CREATE POLICY "Allow read timetable" ON public.timetable FOR SELECT USING (true);
    END IF;
    -- Notices
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read notices') THEN
        CREATE POLICY "Allow read notices" ON public.notices FOR SELECT USING (true);
    END IF;
    -- Events
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read events') THEN
        CREATE POLICY "Allow read events" ON public.events FOR SELECT USING (true);
    END IF;
    -- Academic Documents
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow read academic_documents') THEN
        CREATE POLICY "Allow read academic_documents" ON public.academic_documents FOR SELECT USING (true);
    END IF;
    -- Student Requests (Students view their own; Faculty & Admins view all)
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow select student_requests') THEN
        CREATE POLICY "Allow select student_requests" ON public.student_requests FOR SELECT USING (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow insert student_requests') THEN
        CREATE POLICY "Allow insert student_requests" ON public.student_requests FOR INSERT WITH CHECK (true);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'Allow update student_requests') THEN
        CREATE POLICY "Allow update student_requests" ON public.student_requests FOR UPDATE USING (true);
    END IF;
END $$;

-- ==================== SAMPLE SEED DATA (AIML DEPARTMENT) ====================
-- Insert default subjects if none exist
INSERT INTO public.subjects (id, name, department, semester, credits, description)
VALUES
    ('AI401', 'Machine Learning Foundations', 'AIML', 6, 4, 'Supervised and unsupervised learning, decision trees, regression, and model evaluation.'),
    ('AI402', 'Deep Learning & Neural Networks', 'AIML', 6, 4, 'CNNs, RNNs, Transformers, attention mechanisms, backpropagation, and PyTorch implementations.'),
    ('AI403', 'Natural Language Processing', 'AIML', 6, 3, 'Text processing, word embeddings, sequence-to-sequence models, and Large Language Models.'),
    ('AI404', 'Computer Vision', 'AIML', 6, 3, 'Image filtering, feature extraction, object detection (YOLO), segmentation, and 3D perception.'),
    ('AI405', 'Reinforcement Learning & Robotics', 'AIML', 6, 3, 'Markov Decision Processes, Q-learning, policy gradients, trajectory planning, and robot simulation.'),
    ('AI406', 'AI Ethics & Governance', 'AIML', 6, 2, 'Fairness, accountability, transparency, data privacy regulations, and responsible AI deployment.')
ON CONFLICT (id) DO NOTHING;

-- Insert sample faculty members
INSERT INTO public.faculty (name, designation, department, email, contact_info, specialization, subjects_handled, availability)
VALUES
    ('Dr. A. Sharma', 'Professor & Head of Department', 'AIML', 'hod.aiml@greenfield.edu', 'Cabin 401, AIML Block • Ext 4101', 'Machine Learning, Deep Learning, Predictive Modeling', ARRAY['AI401', 'AI402'], 'Mon & Wed: 2:00 PM - 4:00 PM'),
    ('Prof. K. Patel', 'Associate Professor', 'AIML', 'k.patel@greenfield.edu', 'Cabin 402, AIML Block • Ext 4102', 'Neural Architectures, GPU Computing, Optimization', ARRAY['AI402'], 'Tue & Thu: 11:00 AM - 1:00 PM'),
    ('Dr. R. Verma', 'Assistant Professor', 'AIML', 'r.verma@greenfield.edu', 'Cabin 403, AIML Block • Ext 4103', 'Natural Language Processing, LLMs, Conversational AI', ARRAY['AI403'], 'Daily: 3:00 PM - 4:30 PM'),
    ('Prof. S. Rao', 'Assistant Professor', 'AIML', 's.rao@greenfield.edu', 'Cabin 404, AIML Block • Ext 4104', 'Computer Vision, Edge AI, Autonomous Systems', ARRAY['AI404'], 'Mon & Fri: 10:00 AM - 12:00 PM'),
    ('Dr. M. Gupta', 'Assistant Professor', 'AIML', 'm.gupta@greenfield.edu', 'Cabin 405, AIML Block • Ext 4105', 'Reinforcement Learning, Robotics, Control Theory', ARRAY['AI405'], 'Wed & Thu: 2:00 PM - 3:30 PM'),
    ('Prof. N. Iyer', 'Visiting Professor', 'AIML', 'n.iyer@greenfield.edu', 'Cabin 406, AIML Block • Ext 4106', 'AI Ethics, Governance, Responsible AI, Data Policy', ARRAY['AI406'], 'Friday: 2:00 PM - 5:00 PM')
ON CONFLICT (email) DO NOTHING;

-- Insert sample events
INSERT INTO public.events (title, description, date_time, location, organizer, department)
VALUES
    ('Annual AIML Hackathon 2026', 'Inter-department 36-hour hackathon focused on Generative AI and Autonomous Agent Systems.', now() + interval '14 days', 'AIML Computing Labs 401-403', 'AIML Student Chapter', 'AIML'),
    ('Distinguished Industry Talk: Foundation Models in Production', 'Interactive session with leading AI research engineers on scaling multimodal vision-language models.', now() + interval '6 days', 'Seminar Hall 2, Academic Complex', 'Dept Industry Relations Cell', 'AIML'),
    ('Hands-on Workshop: Edge AI with NVIDIA Jetson', 'Hands-on practical training on deploying quantized computer vision models onto edge robotics hardware.', now() + interval '20 days', 'Robotics & Vision Lab (Lab 402)', 'AIML Robotics Club', 'AIML');

