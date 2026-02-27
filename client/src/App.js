import { HTTPAudioProvider } from './context/HTTPContext';
import { NavbarProvider } from './context/NavbarContext';
import { WSProvider } from './context/WSContext';
import Navbar from './components/Navbar';
import Section from './components/Section';
import Music from './components/Music';
import Ambient from './components/Ambient';
import FX from './components/FX';
import Modulator from './components/Modulator';
import ModulatorEditor from './components/ModulatorEditor';
import './icons';
import './App.css';

function App() {
  return (
    <div className="root">
      <WSProvider>
        <HTTPAudioProvider>
          <NavbarProvider>
            <Navbar />
          </NavbarProvider>
          <div className='sections'>
            <Section id="section-music" header='Music'>
              <Music />
            </Section>
            <Section id="section-ambient" header='Ambient'>
              <Ambient />
            </Section>
            <Section id="section-fx" header='FX'>
              <FX />
            </Section>
            <Section id="section-voice" header='Modulator'>
              <Modulator />
            </Section>
            <Section header='Modulator Editor'>
              <ModulatorEditor
                onPlay={(params) => console.log(params)}
                onSubmit={(params) => console.log(params)}
              />
            </Section>
          </div>
        </HTTPAudioProvider>
      </WSProvider>
    </div>
  );
}

export default App;
