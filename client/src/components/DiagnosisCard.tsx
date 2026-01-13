import { AlertTriangle, Beaker, ChevronDown, ChevronUp, TrendingUp } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";

interface Diagnosis {
  diagnos: string;
  sannolikhet: "hög" | "medel" | "låg";
  beskrivning: string;
  varningsflaggor?: string[];
  utredning?: string[];
}

interface DiagnosisCardProps {
  diagnosis: Diagnosis;
  index: number;
}

const probabilityConfig = {
  hög: {
    badge: "bg-destructive/10 text-destructive border-destructive/30 hover:bg-destructive/15",
    indicator: "bg-gradient-to-r from-destructive to-destructive/80",
    label: "Hög sannolikhet",
  },
  medel: {
    badge: "bg-warning/10 text-warning border-warning/30 hover:bg-warning/15",
    indicator: "bg-gradient-to-r from-warning to-warning/80",
    label: "Medel sannolikhet",
  },
  låg: {
    badge: "bg-muted text-muted-foreground border-border hover:bg-muted/80",
    indicator: "bg-gradient-to-r from-muted-foreground/50 to-muted-foreground/30",
    label: "Låg sannolikhet",
  },
};

export function DiagnosisCard({ diagnosis, index }: DiagnosisCardProps) {
  const [expanded, setExpanded] = useState(index === 0);
  const config = probabilityConfig[diagnosis.sannolikhet];

  return (
    <div 
      className="animate-slide-up group"
      style={{ animationDelay: `${index * 80}ms` }}
    >
      <div className="glass-card rounded-2xl overflow-hidden hover:shadow-2xl hover:shadow-primary/10 transition-all duration-300">
        {/* Probability indicator bar */}
        <div className={`h-1 ${config.indicator}`} />
        
        <div 
          className="p-5 cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-3">
                <span className="flex items-center justify-center w-8 h-8 rounded-xl bg-gradient-to-br from-primary/20 to-accent/20 text-primary text-sm font-display font-bold">
                  {index + 1}
                </span>
                <h3 className="text-lg font-display font-semibold text-foreground truncate group-hover:text-primary transition-colors">
                  {diagnosis.diagnos}
                </h3>
              </div>
              <Badge 
                variant="outline" 
                className={`${config.badge} font-medium transition-colors`}
              >
                <TrendingUp className="w-3 h-3 mr-1.5" />
                {config.label}
              </Badge>
            </div>
            <button className="p-2 rounded-xl hover:bg-muted/80 transition-colors text-muted-foreground hover:text-foreground">
              {expanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
            </button>
          </div>
        </div>
        
        {expanded && (
          <div className="px-5 pb-5 space-y-5 animate-fade-in border-t border-border/30 pt-5">
            <p className="text-muted-foreground leading-relaxed">
              {diagnosis.beskrivning}
            </p>

            {diagnosis.varningsflaggor && diagnosis.varningsflaggor.length > 0 && (
              <div className="p-4 rounded-xl bg-destructive/5 border border-destructive/20 space-y-3">
                <h4 className="text-sm font-semibold flex items-center gap-2 text-destructive">
                  <AlertTriangle size={16} />
                  Varningsflaggor
                </h4>
                <ul className="space-y-2">
                  {diagnosis.varningsflaggor.map((flag, i) => (
                    <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-destructive mt-2 flex-shrink-0" />
                      {flag}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {diagnosis.utredning && diagnosis.utredning.length > 0 && (
              <div className="p-4 rounded-xl bg-primary/5 border border-primary/20 space-y-3">
                <h4 className="text-sm font-semibold flex items-center gap-2 text-primary">
                  <Beaker size={16} />
                  Förslag på utredning
                </h4>
                <ul className="space-y-2">
                  {diagnosis.utredning.map((item, i) => (
                    <li key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary mt-2 flex-shrink-0" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}