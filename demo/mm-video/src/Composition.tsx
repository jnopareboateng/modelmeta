import { Composition } from "remotion";
import { Demo } from "./Demo";

export const MyComposition = () => {
  return (
    <Composition
      id="ModelmetaDemo"
      component={Demo}
      durationInFrames={1437}
      fps={30}
      width={1080}
      height={1080}
    />
  );
};

export const MyComponent: React.FC = () => {
  return null;
};
