import { LandingNav } from "@/components/landing/LandingNav";
import { HeroSection } from "@/components/landing/HeroSection";
import { WhatIsSection, FeaturesSection } from "@/components/landing/LandingSections";
import {
  AudienceSection,
  FinalCtaSection,
  HowItWorksSection,
  LandingFooter,
  MetricsSection,
  PlatformPreviewSection,
  WhyAISection,
} from "@/components/landing/LandingSections2";

export default function LandingPage() {
  return (
    <div className="landing-page min-h-screen bg-[#05070a] text-white">
      <LandingNav />
      <main>
        <HeroSection />
        <WhatIsSection />
        <FeaturesSection />
        <PlatformPreviewSection />
        <HowItWorksSection />
        <AudienceSection />
        <WhyAISection />
        <MetricsSection />
        <FinalCtaSection />
      </main>
      <LandingFooter />
    </div>
  );
}
