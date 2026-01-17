import React, { useEffect } from 'react';
import { IntertekLogo } from './LetterComponents/IntertekLogo';
import './LetterPage.css';
import LetterSmartField from './LetterComponents/LetterSmartField';
import { getLetterItem } from '../../utils/letterResolver';
import { formatIssueDate } from './LetterComponents/formatIssueDate';

const LetterPage2 = ({
  json,
  editMode,
  handleApprove,
  openComment,
  onBookmarkClick,
}) => {
  const [, forceUpdate] = React.useReducer((x) => x + 1, 0);
  useEffect(() => {
    const item1 = getLetterItem(json, '«IssuedDate»'); // Issue Date key
    if (!item1) return;
    const item2 = getLetterItem(json, '«ProjectNumber»');
    if (!item2) return;
    // Only auto-fill once
    if (!item1.value) {
      item1.value = formatIssueDate();
      item1.is_user_edited = false; // system-filled
      forceUpdate();
    }
    if (!item2.value) {
      item2.value = localStorage.getItem('projectId');
      item2.is_user_edited = false;
      forceUpdate();
    }
  }, [json]);
  return (
    <div className="letter-page">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          color: 'grey',
          fontSize: '13px',
        }}
      >
        <IntertekLogo />
        <div>
          <div style={{ marginBottom: '3%' }}>
            <span>1809 10th St, Suite 400</span>
            <br />
            <span>Plano, TX 75074 </span>
          </div>
          <div>
            <span>Telephone: (972) 202-8800 </span>
            <br />
            <span>Facsimile: (972) 202-8801 </span>
            <br />
            <span>www.intertek.com</span>
          </div>
        </div>
      </div>
      <h3 style={{ marginBottom: '5%' }}>Letter Report</h3>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <div>
          <div>
            <LetterSmartField
              json={json}
              name="«IssuedDate»"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
          <br />
          <div>
            <LetterSmartField
              json={json}
              name="«AppContactName»"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
          <br />
          <div>
            <LetterSmartField
              json={json}
              name="«AppCOMPANYNAME»"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
          <br />
          <div>
            <LetterSmartField
              json={json}
              name="«AppStreetAddress»"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
          <br />
          <div>
            <LetterSmartField
              json={json}
              name="«AppCityStZip»"
              editMode={editMode}
              onChange={forceUpdate}
              onApprove={handleApprove}
              onComment={openComment}
              onBookmark={onBookmarkClick}
            />
          </div>
        </div>
        <div style={{ width: '40%' }}>
          {/* Report Number */}
          <div style={{ display: 'flex' }}>
            <span style={{ width: '40%' }}>Intertek Report No.</span>
            <span style={{ width: '60%' }}>
              <LetterSmartField
                json={json}
                name="«ReportNumber»"
                editMode={editMode}
                onChange={forceUpdate}
                onApprove={handleApprove}
                onComment={openComment}
                onBookmark={onBookmarkClick}
              />
            </span>
          </div>

          <br />

          {/* Project Number */}
          <div style={{ display: 'flex' }}>
            <span style={{ width: '40%' }}>Intertek Project No.</span>
            <span style={{ width: '60%' }}>
              <LetterSmartField
                json={json}
                name="«ProjectNumber»"
                editMode={editMode}
                onChange={forceUpdate}
                onApprove={handleApprove}
                onComment={openComment}
                onBookmark={onBookmarkClick}
              />
            </span>
          </div>

          <br />

          {/* Phone */}
          <div style={{ display: 'flex' }}>
            <span style={{ width: '40%' }}>Ph:</span>
            <span style={{ width: '60%' }}>
              <LetterSmartField
                json={json}
                name="«AppPhone»"
                editMode={editMode}
                onChange={forceUpdate}
                onApprove={handleApprove}
                onComment={openComment}
                onBookmark={onBookmarkClick}
              />
            </span>
          </div>

          <br />

          {/* Fax */}
          <div style={{ display: 'flex' }}>
            <span style={{ width: '40%' }}>Fx:</span>
            <span style={{ width: '60%' }}>
              <LetterSmartField
                json={json}
                name="«AppFax»"
                editMode={editMode}
                onChange={forceUpdate}
                onApprove={handleApprove}
                onComment={openComment}
                onBookmark={onBookmarkClick}
              />
            </span>
          </div>

          <br />

          {/* Email */}
          <div style={{ display: 'flex' }}>
            <span style={{ width: '40%' }}>Email:</span>
            <span style={{ width: '60%' }}>
              <LetterSmartField
                json={json}
                name="«AppEmail»"
                editMode={editMode}
                onChange={forceUpdate}
                onApprove={handleApprove}
                onComment={openComment}
                onBookmark={onBookmarkClick}
              />
            </span>
          </div>
        </div>
      </div>
      <div style={{ marginTop: '5%', marginBottom: '5%' }}>
        Subject:{' '}
        <LetterSmartField
          json={json}
          name="<ETL Listing/CB/Other Evaluation> of the «ProductType» «ProductCovModels»"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
          wide
        />
      </div>

      <div>
        Dear Mr.{' '}
        <LetterSmartField
          json={json}
          name="«AppContactName»"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
      </div>
      <p>
        This letter report represents the results of our evaluation of the above
        referenced product(s) to the requirements contained in the following
        standards:
      </p>
      <div>
        <LetterSmartField
          json={json}
          name="«StandardTitleNoEdDate»"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
      </div>
      <h3 className="section">
        SECTION 1<br />
      </h3>
      <span>
        <b>SUMMARY</b>
      </span>
      <br />
      <br />
      <div>
        Intertek wishes to inform you that, during our{' '}
        <LetterSmartField
          json={json}
          name="evaluation (Stage 1) or/and testing (Stage 2)"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />
        , non-conformances or additional information have been identified.{' '}
      </div>
      <div>
        <p>
          Due to the nature of these items, the project has been placed{` `}
          <b>on-hold</b> awaiting resolutions from you to address the items
          detailed in this letter report.
        </p>
      </div>
      <div>
        <p>
          Your assigned Intertek Project Manager will be in contact with you
          shortly to discuss the following:
        </p>
      </div>
      <div>
        <ul className="arrow-list">
          <li>
            {' '}
            The timelines for supplying resolutions to all findings detailed in
            this letter report.
          </li>
          <li>
            Any additional or repeat work required which will be subject to a
            Project Change Order Request (PCOR), and any additional associated
            costs.
          </li>
        </ul>
      </div>
      <div className="letter-line">
        <span>A draft copy of the </span>
        <LetterSmartField
          json={json}
          name="<CB Test Report/ETL CDR/Deliverable>"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />

        <span> </span>
        <LetterSmartField
          json={json}
          name="<will be sent under separate cover/attached to this letter>"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />

        <span>
          {' '}
          for you to review. We kindly ask you to check and confirm that all
          information supplied for your{' '}
        </span>

        <LetterSmartField
          json={json}
          name="<product(s)/system/etc>"
          editMode={editMode}
          onChange={forceUpdate}
          onApprove={handleApprove}
          onComment={openComment}
          onBookmark={onBookmarkClick}
        />

        <span>
          {' '}
          is correct and accurate, and reply back to us promptly if there are
          any discrepancies. Please contact either your assigned Intertek
          Project Manager or Intertek Engineer who will assist you, if required.
        </span>
      </div>

      <div>
        <p>
          To assist you in addressing these issues, we have outlined these
          below. Each item is identified by the clause of the applicable
          standard.{' '}
        </p>
      </div>
    </div>
  );
};

export default LetterPage2;
