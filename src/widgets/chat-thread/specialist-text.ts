import type { Summary } from "@/entities/chat";

export function specialistText(summary: Summary): string {
    const details = summary.case;
    const complaints = [
        ...details.manifestations.map(({ name }) => name),
        ...details.unrecognized,
    ];
    const duration = details.duration_weeks;

    const facts: string[] = [];
    if (complaints.length) {
        facts.push(`Что беспокоит: ${complaints.join(", ")}`);
    }
    if (details.stressors.length) {
        facts.push(`Обстоятельства: ${details.stressors.map(({ name }) => name).join(", ")}`);
    }
    if (duration !== null) {
        const label = duration === 0 ? "меньше недели" : `от ${duration} нед.`;
        facts.push(`Длительность: ${label}`);
    }
    if (details.affected_domains.length) {
        facts.push(
            `Сказывается на сферах жизни: ${details.affected_domains.map(({ name }) => name).join(", ")}`,
        );
    }
    if (details.goal) {
        facts.push(`Цель консультации: ${details.goal}`);
    }
    if (!facts.length) {
        return summary.specialist_request;
    }
    return `${summary.specialist_request}\n\n${facts.join("\n")}`;
}
