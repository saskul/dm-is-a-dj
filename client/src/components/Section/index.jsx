import './index.css';

const Section = ({ id, header, children }) => (
  <section id={id} className='section noselect'>
    <h2>{header}</h2>
    {children}
  </section>
);

export default Section;