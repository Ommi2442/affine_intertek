import React from 'react';
import './OptionTable.css';

const OptionTable = () => {
  return (
    <div className="option-table">
      {/* Header */}
      <div className="opt-header">
        <div className="opt-cell opt-option">OPTION</div>
        <div className="opt-cell opt-desc">DESCRIPTION</div>
        <div className="opt-cell opt-check"></div>
      </div>

      {/* Option 1 */}
      <div className="opt-row">
        <div className="opt-cell opt-option">1</div>

        <div className="opt-cell opt-desc">
          <p>
            We will supply resolutions to address ALL failures <u>item</u>{' '}
            identified along with modified sample(s) and documentation requested
            in this Letter Report (if applicable)
          </p>

          <p>
            Once the modifications and documents necessary to address ALL of the
            issues have been complied, please contact your dedicated Intertek
            Project Manager to initiate continuing the evaluation or follow-up
            evaluation.
          </p>

          <p>
            <b>Client Ready Date:</b>
          </p>

          <p className="note">
            <i>
              Note 1: As the project has been placed on-hold, Intertek reserve
              the right to invoice for work completed.
            </i>
          </p>

          <p className="note">
            <i>
              Note 2: This may require a PCOR – Project Change Order Request to
              cover the additional scope of work necessary to review your
              responses and complete the project. This will be issued via your
              Account Manager.
            </i>
          </p>

          <p className="note">
            <i>
              Note 3: Intertek upon receipt of ALL resolutions/modified sample/s
              & PCOR approval (if required) will reschedule the project at the
              next available opportunity.
            </i>
          </p>
        </div>

        <div className="opt-cell opt-check">
          <div className="checkbox" />
        </div>
      </div>

      {/* Option 2 */}
      <div className="opt-row">
        <div className="opt-cell opt-option">2</div>

        <div className="opt-cell opt-desc">
          <p>
            Please halt all further testing at this stage and invoice my project
            for work completed to date.
          </p>
        </div>

        <div className="opt-cell opt-check">
          <div className="checkbox" />
        </div>
      </div>
    </div>
  );
};

export default OptionTable;
