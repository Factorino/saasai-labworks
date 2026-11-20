import type { FactKind, Summary } from "@/entities/chat";

export const FACT_LABELS: Readonly<Record<FactKind, string>> = {
    manifestations: "Проявления",
    duration: "Длительность",
    frequency: "Частота",
    impact: "Влияние на жизнь",
    affected_domains: "Затронутые сферы",
    self_harm: "Скрининг самоповреждения",
    sleep: "Сон",
    appetite: "Аппетит",
    energy: "Энергия",
    substance_use: "Употребление веществ",
    goal: "Цель консультации",
};

const FREQUENCY_LABELS = [
    "Редко",
    "Несколько раз в неделю",
    "Большую часть дней",
    "Постоянно",
] as const;
const IMPACT_LABELS = [
    "Почти не мешает",
    "Немного мешает",
    "Заметно мешает",
    "Очень сильно мешает",
] as const;
const SCREENING_LABELS = {
    none: "Нет",
    passive: "Пассивные мысли",
    active: "Активные мысли",
    plan: "Есть план",
    unknown: "Неизвестно",
};
const CHANGE_LABELS = {
    unchanged: "Без изменений",
    decreased: "Снижение",
    increased: "Повышение",
};

function nameOf<Key extends PropertyKey>(
    value: Key | null,
    labels: Readonly<Record<Key, string>>,
) {
    return value === null ? null : labels[value];
}

export function caseFacts(summary: Summary): readonly (readonly [string, string])[] {
    const data = summary.case;

    const fields: readonly (readonly [string, string | null])[] = [
        [
            FACT_LABELS.duration,
            data.duration_weeks === null ? null : `${data.duration_weeks} нед.`,
        ],
        [FACT_LABELS.frequency, data.frequency === null ? null : FREQUENCY_LABELS[data.frequency]],
        [FACT_LABELS.impact, data.impact === null ? null : IMPACT_LABELS[data.impact]],
        [FACT_LABELS.self_harm, nameOf(data.self_harm, SCREENING_LABELS)],
        [FACT_LABELS.sleep, nameOf(data.sleep, CHANGE_LABELS)],
        [FACT_LABELS.appetite, nameOf(data.appetite, CHANGE_LABELS)],
        [FACT_LABELS.energy, nameOf(data.energy, CHANGE_LABELS)],
        [
            FACT_LABELS.substance_use,
            data.substance_use === null ? null : data.substance_use ? "Да" : "Нет",
        ],
        [FACT_LABELS.goal, data.goal],
        ["Жалобы вне онтологии", data.unrecognized.join(", ") || null],
        [
            "Недостающие сведения",
            summary.missing.map((fact) => FACT_LABELS[fact]).join(", ") || null,
        ],
        ["Отказ от ответа", data.refused.map((fact) => FACT_LABELS[fact]).join(", ") || null],
    ];
    return fields.filter((field): field is readonly [string, string] => field[1] !== null);
}
