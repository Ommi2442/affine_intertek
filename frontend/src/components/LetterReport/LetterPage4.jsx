import React from 'react';
import { IntertekLogo } from './LetterComponents/IntertekLogo';

const LetterPage4 = () => {
  return (
    <div className="letter-page">
      <IntertekLogo />
      <h3 style={{ marginBottom: '5%' }}>Letter Report</h3>
      <p>
        Details for the following critical components or materials have not been
        provided as required:
      </p>
      <p>
        Please provide information highlighted in yellow and verify all other
        information present in the above table.{' '}
      </p>

      <h3 className="section">
        SECTION 4<br />
      </h3>
      <span>
        <b>TESTING</b>
      </span>
      <div>
        <p>
          The below listed represents a summary of the tests & results,
          including any which are pending completion or have yet to be
          conducted.
        </p>
      </div>
      <div>
        <p>
          <u> Completed Tests:</u>
        </p>
        <p>Test Location: </p>
      </div>
      {/* static table */}
      <table className="test-table">
        <thead>
          <tr>
            <th>Test Description</th>
            <th>Standard</th>
            <th>Section</th>
            <th>Results</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
          </tr>
          <tr>
            <td></td>
            <td></td>
            <td></td>
            <td></td>
          </tr>
        </tbody>
      </table>

      <div>
        <p>
          <u>Pending Tests:</u>
        </p>
      </div>
      {/* static table */}
      <table className="test-table">
        <thead>
          <tr>
            <th>Test Description</th>
            <th>Standard</th>
            <th>Section</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td></td>
            <td></td>
            <td></td>
          </tr>
          <tr>
            <td></td>
            <td></td>
            <td></td>
          </tr>
        </tbody>
      </table>
    </div>
  );
};

export default LetterPage4;
