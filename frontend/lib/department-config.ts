/**
 * department-config.ts — Department-specific configuration for AIDA.
 * Provides client-side constants and defaults for the AIML Department.
 */

export interface DepartmentCourse {
    id: string;
    name: string;
    semester: number;
    credits: number;
}

export interface DepartmentLab {
    id: string;
    name: string;
    room: string;
    in_charge_title: string;
}

export interface DepartmentConfig {
    code: string;
    name: string;
    acronym: string;
    institution: string;
    sections: string[];
    courses: DepartmentCourse[];
    labs: DepartmentLab[];
    document_categories: string[];
}

export const DEFAULT_DEPARTMENT_CONFIG: DepartmentConfig = {
    code: "AIML",
    name: "Artificial Intelligence & Machine Learning",
    acronym: "AIML",
    institution: "Department of AIML",
    sections: ["AIML-A", "AIML-B"],
    courses: [
        { id: "AI401", name: "Machine Learning Foundations", semester: 6, credits: 4 },
        { id: "AI402", name: "Deep Learning & Neural Networks", semester: 6, credits: 4 },
        { id: "AI403", name: "Natural Language Processing", semester: 6, credits: 3 },
        { id: "AI404", name: "Computer Vision", semester: 6, credits: 3 },
        { id: "AI405", name: "Reinforcement Learning & Robotics", semester: 6, credits: 3 },
        { id: "AI406", name: "AI Ethics & Governance", semester: 6, credits: 2 }
    ],
    labs: [
        { id: "LAB-AIML-01", name: "High Performance AI & Deep Learning Lab", room: "Lab 401, AIML Block", in_charge_title: "Faculty Lab In-Charge (Deep Learning)" },
        { id: "LAB-AIML-02", name: "Computer Vision & Robotics Lab", room: "Lab 402, AIML Block", in_charge_title: "Faculty Lab In-Charge (Robotics)" },
        { id: "LAB-AIML-03", name: "Natural Language & Speech Systems Lab", room: "Lab 403, AIML Block", in_charge_title: "Faculty Lab In-Charge (NLP)" }
    ],
    document_categories: [
        "Curriculum & Syllabus",
        "Lab Manuals",
        "Capstone Project Guidelines",
        "Academic Regulations & Evaluation",
        "Faculty Directory & Office Hours",
        "Department Circulars & Policies"
    ]
};

