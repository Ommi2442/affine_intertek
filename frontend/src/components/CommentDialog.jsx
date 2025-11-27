import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Box,
  Typography,
  IconButton,
  Button,
  Divider,
  Paper,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';

const CommentDialog = ({
  open,
  onClose,
  comments = [],
  currentComment,
  setCurrentComment,
  onSubmit,
}) => {
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      {/* Header */}
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          p: 2,
        }}
      >
        <Typography variant="h6" noWrap>
          Comments
        </Typography>
        <IconButton onClick={onClose}>
          <CloseIcon />
        </IconButton>
      </DialogTitle>

      <Divider />

      {/* Existing Comments */}
      <DialogContent
        sx={{
          maxHeight: 250,
          overflowY: 'auto',
          p: 2,
          width: '100%',
          boxSizing: 'border-box',
        }}
      >
        {comments.length === 0 ? (
          <Typography
            variant="body2"
            color="text.secondary"
            sx={{ wordBreak: 'break-word' }}
          >
            No comments yet.
          </Typography>
        ) : (
          comments.map((c, idx) => (
            <Paper
              key={idx}
              variant="outlined"
              sx={{
                p: 1,
                mb: 1,
                wordBreak: 'break-word',
                whiteSpace: 'pre-wrap',
                width: '100%',
                boxSizing: 'border-box',
              }}
            >
              <Typography variant="body2">{c}</Typography>
            </Paper>
          ))
        )}
      </DialogContent>

      {/* Add Comment Textarea */}
      <Box sx={{ px: 2, pb: 2, width: '100%', boxSizing: 'border-box' }}>
        <textarea
          value={currentComment}
          onChange={(e) => setCurrentComment(e.target.value)}
          placeholder="Add your comment"
          style={{
            width: '100%',
            minHeight: '80px',
            padding: '8px',
            fontSize: '14px',
            borderRadius: '6px',
            border: '1px solid #ccc',
            resize: 'vertical',
            boxSizing: 'border-box',
            overflowWrap: 'break-word',
          }}
        />
      </Box>

      {/* Submit Button */}
      <DialogActions sx={{ px: 2, pb: 2 }}>
        <Button
          onClick={onSubmit}
          variant="contained"
          sx={{
            backgroundColor: '#000',
            color: '#fff',
            width: '100%',
            '&:hover': { backgroundColor: '#333' },
          }}
        >
          Submit
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CommentDialog;
