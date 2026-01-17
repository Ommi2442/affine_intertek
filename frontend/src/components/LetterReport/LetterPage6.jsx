import React from 'react';
import { IntertekLogo } from './LetterComponents/IntertekLogo';
import OptionTable from './LetterComponents/OptionTable';
import SimpleSignatureBlock from './LetterComponents/SimpleSignatureBlock';

const LetterPage6 = ({ json }) => {
  return (
    <div className="letter-page">
      <IntertekLogo />
      <h3 style={{ marginBottom: '5%' }}>Letter Report</h3>
      <h3>PLEASE RETURN THIS PAGE TO THE INTERTEK PROJECT MANAGER</h3>
      <p>
        <b>Project Manager Name:</b> Theresa Reinhardt
      </p>
      <p>
        Please advise which of the following options <b>you</b> wish us to
        pursue
      </p>
      <OptionTable json={json} />
      <br />
      <br />
      <br />
      <br />
      <SimpleSignatureBlock json={json} />
    </div>
  );
};

export default LetterPage6;
