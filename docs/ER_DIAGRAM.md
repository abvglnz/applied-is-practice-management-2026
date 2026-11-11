# Практиканы басқару жүйесінің ER схемасы

```mermaid
erDiagram
    STUDENTS ||--o{ PLACEMENTS : "практикаға бөлінеді"
    BASES ||--o{ PLACEMENTS : "практика өтетін орын"
    SUPERVISORS ||--o{ PLACEMENTS : "жетекшілік етеді"
    BASES ||--o{ CONTRACTS : "келісімшарт жасайды"
    CONTRACTS ||--o{ PLACEMENTS : "негіз болады"
    PLACEMENTS ||--o{ DIARIES : "күнделік жүргізеді"
    PLACEMENTS ||--o| REPORTS : "есеп тапсырады"
    PLACEMENTS ||--o| GRADES : "бағаланады"

    STUDENTS {
        int id PK
        string name
        string group_name
        string email
    }
    BASES {
        int id PK
        string name
        string address
        string contact
        int capacity
    }
    SUPERVISORS {
        int id PK
        string name
        string position
        string email
    }
    CONTRACTS {
        int id PK
        string number
        int base_id FK
        date start_date
        date end_date
    }
    PLACEMENTS {
        int id PK
        int student_id FK
        int base_id FK
        int supervisor_id FK
        int contract_id FK
        string kind
        date start_date
        date end_date
    }
    DIARIES {
        int id PK
        int placement_id FK
        date date
        string content
        int hours
        string status
    }
    REPORTS {
        int id PK
        int placement_id FK
        string title
        string status
    }
    GRADES {
        int id PK
        int placement_id FK
        int discipline
        int diary
        int report
        int defense
    }
```

Негізгі байланыстар `schema.sql` ішінде сыртқы кілттермен бекітілген. SQLModel-дегі `Relationship` объектілері Python кодында осы байланыстар бойынша өтуге мүмкіндік береді.
